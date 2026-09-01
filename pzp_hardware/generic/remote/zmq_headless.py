import gzip
import hashlib
import pickle
import logging

from puzzlepiece.extras import hardware_tools as pht
pht.requirements({
    "zmq": {
        "pip": "pyzmq"
    }
})
import zmq

class _ZMQCommsBase:
    """
    An abstract object implementing some of the basics of the ZMQ-based
    communication protocol we use here.
    """

    def verify_hash(self, content, salt):
        """
        Unpickling is in general an unsafe operation, so we verify a hash here
        to make sure we can trust the client that sent the message
        """
        m = hashlib.sha256()
        m.update(content[32:])
        m.update(salt.encode())
        return m.digest() == content[:32]

    def encode_message(self, data, salt, status=0):
        """
        Encode the provided data (arbitrary Python object) for sending by
        pickling and gzipping it, prepending a hash and a status value.
        """
        data = gzip.compress(
            pickle.dumps(data),
            compresslevel=1
        )

        m = hashlib.sha256()
        m.update(data)
        m.update(salt.encode())

        return (
            status.to_bytes(1, byteorder='big') +
            m.digest() +
            data
        )

    def decode_message(self, message, salt):
        """
        Encode the provided message and return the data and status code within.
        """
        status = int(message[0])

        if self.verify_hash(message[1:], salt):
            data = gzip.decompress(message[33:])
            data = pickle.loads(data)
            return status, data
        else:
            return 1, "Incorrect hash"


class Client(_ZMQCommsBase):
    def __init__(self, address, port, salt):
        self.address = address
        self.port = port
        self.salt = salt
        self.socket = None

    @property
    def context(self):
        if not hasattr(self, "_context"):
            self._context = zmq.Context()
        return self._context

    def send(self, data=None):
        response = None
        data = data or b""
        message = self.encode_message(data, self.salt)

        # This follows the "Lazy Pirate" pattern from the ZMQ book:
        # https://zguide.zeromq.org/docs/chapter4/#Client-Side-Reliability-Lazy-Pirate-Pattern
        for i in range(3):
            if self.socket is None:
                logging.info("Client connecting to server...")
                self.socket = self.context.socket(zmq.REQ)
                self.socket.connect(f"tcp://{self.address}:{self.port}")

            logging.debug("Client sending request")
            self.socket.send(message)

            if (self.socket.poll(3000) & zmq.POLLIN) != 0:
                response = self.socket.recv()
                logging.debug("Client received %s", response)
                break
            else:
                logging.warning("Client saw no response from server on attempt %s", i)
                self.socket.setsockopt(zmq.LINGER, 0)
                self.socket.close()
                self.socket = None
                logging.info("Client disconnected")

        if response is None:
            raise Exception("Server seems to be offline, client abandoning")

        status, data = self.decode_message(response, self.salt)

        if not status:
            return data
        else:
            error = f"Error: {data}"
        logging.error(error)
        return error
