import json
import logging
import signal
import socket
import socketserver
import sys

from sympy import O

import constants
import ismrmrd
import process


class LoggingHandler(logging.Handler):
    """Loggger that sends logs as MRD messages."""

    def __init__(self, socket: socket.socket):
        super().__init__()
        self.socket = socket

    def emit(self, record):
        try:
            self.socket.send(constants.MrdMessageIdentifier.pack(constants.MRD_MESSAGE_TEXT))
            data = f"{self.format(record)}\0".encode()
            self.socket.send(constants.MrdMessageLength.pack(len(data)))
            self.socket.send(data)
        except OSError:
            pass


class Server(socketserver.BaseRequestHandler):
    """ISMRMRD Server."""

    request: socket.socket

    def read(self, length) -> bytes:
        read = self.request.recv(length, socket.MSG_WAITALL)
        return read

    def read_string(self) -> str:
        length = constants.MrdMessageLength.unpack(self.read(constants.SIZEOF_MRD_MESSAGE_LENGTH))[0]
        data = self.read(length)
        string = data.split(b"\x00", 1)[0].decode("utf-8")
        return string

    def handle(self) -> None:
        """Handle a connection."""
        try:
            logging_handler = LoggingHandler(self.request)
            logging.getLogger().addHandler(logging_handler)

            acquisitions = []
            waveforms = []
            images = []
            config = {}
            metadata = ""

            while True:
                data = self.read(constants.SIZEOF_MRD_MESSAGE_IDENTIFIER)
                identifier = constants.MrdMessageIdentifier.unpack(data)[0]

                match identifier:
                    case constants.MRD_MESSAGE_TEXT:
                        logging.info("Received MRD_MESSAGE_TEXT")
                        config = json.loads(self.read_string())["parameters"]
                        logging.debug("Config: %s", config)

                    case constants.MRD_MESSAGE_METADATA_XML_TEXT:
                        logging.info("Received MRD_MESSAGE_METADATA_XML_TEXT")
                        metadata = self.read_string()
                        logging.debug("XML Metadata: %s", metadata)

                    case constants.MRD_MESSAGE_ISMRMRD_ACQUISITION:
                        logging.info("Received MRD_MESSAGE_ISMRMRD_ACQUISITION")
                        acq = ismrmrd.Acquisition.deserialize_from(self.read)
                        acquisitions.append(acq)

                    case constants.MRD_MESSAGE_ISMRMRD_WAVEFORM:
                        logging.info("Received MRD_MESSAGE_ISMRMRD_WAVEFORM")
                        waveform = ismrmrd.Waveform.deserialize_from(self.read)
                        waveforms.append(waveform)

                    case constants.MRD_MESSAGE_ISMRMRD_IMAGE:
                        logging.info("Received MRD_MESSAGE_ISMRMRD_IMAGE")
                        image = ismrmrd.Image.deserialize_from(self.read)
                        images.append(image)

                    case constants.MRD_MESSAGE_CONFIG_TEXT:
                        logging.info("Received MRD_MESSAGE_CONFIG_TEXT. ignoring.")
                        _ = self.read_string()

                    case constants.MRD_MESSAGE_CONFIG_FILE:
                        logging.info("Received MRD_MESSAGE_CONFIG_FILE. ignoring.")
                        _ = self.read(constants.SIZEOF_MRD_MESSAGE_CONFIGURATION_FILE)

                    case constants.MRD_MESSAGE_CLOSE:
                        logging.info("Received MRD_MESSAGE_CLOSE. Processing data...")
                        images = process.process(acquisitions, config, metadata, images, waveforms)
                        logging.info("Done Processing.")

                        for image in images:
                            logging.info("Sending Image")
                            self.request.sendall(constants.MrdMessageIdentifier.pack(constants.MRD_MESSAGE_ISMRMRD_IMAGE))
                            image.serialize_into(self.request.sendall)

                        logging.info("Sending MRD_MESSAGE_CLOSE")
                        self.request.sendall(constants.MrdMessageIdentifier.pack(constants.MRD_MESSAGE_CLOSE))
                        break

                    case _:
                        logging.warning("Received unsupported message identifier: %d", identifier)

            logging.info("Closing connection")

        except Exception as e:
            logging.exception("Error handling connection: %s", e)

        finally:
            logging.info("Closing connection")
            logging.getLogger().removeHandler(logging_handler)
            logging_handler.close()
            self.request.close()


def watchdog(signum, frame):
    """Called when the watchdog timer expires."""
    logging.error("Watchdog expired. Exiting.")
    sys.exit(1)


def main() -> None:
    """Main function."""

    # watchdog timer to exit if the server hangs
    signal.signal(signal.SIGALRM, watchdog)
    signal.alarm(120)

    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler(sys.stdout)])

    with socketserver.TCPServer(("0.0.0.0", 9002), Server) as server:  # noqa	S104
        logging.info("Starting server...")
        server.serve_forever()


if __name__ == "__main__":
    main()
