from pzp_hardware.generic.remote import zmq_headless

import puzzlepiece as pzp
from puzzlepiece.extras import hardware_tools as pht
from qtpy import QtWidgets

import logging

pht.requirements({
    "zmq": {
        "pip": "pyzmq"
    }
})
import zmq

class _ZMQ_Piece(pzp.Piece, zmq_headless._ZMQCommsBase):
    def define_params(self):
        self.socket = None
        # Establish a global zmq context for the Puzzle if needed
        if not self.puzzle.globals.require("zmq_context"):
            self.puzzle.globals["zmq_context"] = zmq.Context()
        pzp.param.spinbox(self, "port", 5555)(None)
        pzp.param.text(self, "salt", "CHANGE THIS")(None)

    @property
    def context(self):
        return self.puzzle.globals["zmq_context"]


class Server(_ZMQ_Piece):
    def define_params(self):
        @pzp.param.checkbox(self, "running", 0)
        def running(value):
            if value and not self["running"].value:
                # Start the server in a Worker
                worker = pzp.threads.Worker(self.start_server)
                self.puzzle.run_worker(worker)
            elif not value and self["running"].value:
                # The server detects this flag to stop
                self.stop = True
        super().define_params()
        pzp.param.readout(self, "requests")(None)
        self["requests"].set_value(0)

    def call_stop(self):
        self["running"].set_value(0)

    def start_server(self):
        # Start the server
        self.socket = socket = self.context.socket(zmq.REP)
        socket.bind(f"tcp://*:{self['port'].value}")
        logging.info("Server started")

        # Clear the stop flag and run the server loop
        self.stop = False
        try:
            while True:
                # Poll socket for one second to see if we receive anything
                if (socket.poll(1000) & zmq.POLLIN) != 0:
                    message = socket.recv()
                    self["requests"].set_value(self["requests"].value + 1)
                    logging.debug("Server received: %s", message)
                    # Verify hash
                    status, data = self.decode_message(message, self["salt"].value)
                    if not status:
                        # Process content
                        try:
                            response = self.process_data(data)
                            socket.send(self.encode_message(response, self["salt"].value))
                        except Exception as e:
                            # If an exception occurs, reply with code 2
                            # but don't stop the server
                            logging.exception(e)
                            socket.send(self.encode_message(
                                f'{type(e).__name__}: {e}', 2
                            ))
                    else:
                        # Indicate an error occured if the hash is invalid
                        socket.send(self.encode_message("", 1))
                # Whenever the socket poll times out,
                # check if we want to shut the server down
                if self.stop:
                    break
        finally:
            # try ... finally because we want the server to stop at the end
            # even if errors occur
            logging.info("Server stopped")
            socket.setsockopt(zmq.LINGER, 0)
            self.socket.close()

    def process_data(self, data):
        """
        The data in a message is an arbitrary Python object technically.
        In this default function we run set/get operations if the data is
        a dictionary.

        Override this method to do other things.
        """
        response = {}
        if not isinstance(data, dict):
            return response
        if "set" in data:
            for key in data["set"]:
                self.puzzle[key].set_value(data["set"][key])
        if "get" in data:
            for key in data["get"]:
                response[key] = self.puzzle[key].get_value()
        return response

class Client(_ZMQ_Piece):
    def define_params(self):
        pzp.param.text(self, "address", "localhost")(None)
        super().define_params()

    def define_actions(self):
        @pzp.action.define(self, "Send")
        def send(data=None):
            response = None
            data = data or b""
            message = self.encode_message(data, self["salt"].value)

            # This follows the "Lazy Pirate" pattern from the ZMQ book:
            # https://zguide.zeromq.org/docs/chapter4/#Client-Side-Reliability-Lazy-Pirate-Pattern
            for i in range(3):
                if self.socket is None:
                    logging.info("Client connecting to server...")
                    self.socket = self.context.socket(zmq.REQ)
                    self.socket.connect(f"tcp://{self['address'].value}:{self['port'].value}")

                logging.debug("Client sending request")
                self.socket.send(message)

                if (self.socket.poll(3000) & zmq.POLLIN) != 0:
                    response = self.socket.recv()
                    logging.debug("Client received %s", response)
                    break
                else:
                    logging.warning("Client saw no response from server on attempt %s", i)
                    self.actions["Disconnect"]()

            if response is None:
                raise Exception("Server seems to be offline, client abandoning")

            status, data = self.decode_message(response, self["salt"].value)

            if not status:
                return data
            else:
                error = f"Error: {data}"
            logging.error(error)
            return error

        @pzp.action.define(self, "Disconnect")
        def disconnect():
            if self.socket is not None:
                self.socket.setsockopt(zmq.LINGER, 0)
                self.socket.close()
                self.socket = None
                logging.info("Client disconnected")

    def custom_layout(self):
        layout = QtWidgets.QVBoxLayout()
        self.timer = pzp.threads.PuzzleTimer(
            "heartbeat",
            self.puzzle,
            self.actions["Send"],
            1
        )
        layout.addWidget(self.timer)
        return layout