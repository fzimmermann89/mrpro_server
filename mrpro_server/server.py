import json
import logging
import socketserver

import constants
import ismrmrd
import process


class Server(socketserver.BaseRequestHandler):
    """ISMRMRD Server."""

    def handle(self):
        """Handle a connection."""
        try:
            acqs = []
            config = {}
            metadata: str | None = None
            while True:
                data = self.request.recv(constants.SIZEOF_MRD_MESSAGE_IDENTIFIER)
                identifier = constants.MrdMessageIdentifier.unpack(data)[0]
                if identifier == constants.MRD_MESSAGE_TEXT:
                    logging.info("Received MRD_MESSAGE_TEXT")
                    length = constants.MrdMessageLength.unpack(self.request.recv(constants.SIZEOF_MRD_MESSAGE_LENGTH))[0]
                    text: str = self.request.recv(length).split("\x00", 1)[0].decode("utf-8")
                    logging.debug("Text: %s", text)
                    config = json.loads(text)["parameters"]
                    logging.debug("Config: %s", config)
                elif identifier == constants.MRD_MESSAGE_METADATA_XML_TEXT:
                    logging.info("Received MRD_MESSAGE_METADATA_XML_TEXT")
                    length = constants.MrdMessageLength.unpack(self.request.recv(constants.SIZEOF_MRD_MESSAGE_LENGTH))[0]
                    metadata = self.request.recv(length).decode("utf-8")
                    logging.debug("XML Metadata: %s", metadata)
                elif identifier == constants.MRD_MESSAGE_ISMRMRD_ACQUISITION:
                    logging.info("Received MRD_MESSAGE_ISMRMRD_ACQUISITION")
                    acq = ismrmrd.Acquisition.deserialize_from(self.request.recv)
                    acqs.append(acq)
                elif identifier == constants.MRD_MESSAGE_CLOSE:
                    logging.info("Received MRD_MESSAGE_CLOSE. Processing data...")
                    if metadata is None:
                        raise ValueError("Metadata is required")
                    images = process.process(acqs, config, metadata)
                    for image in images:
                        data = constants.MrdMessageIdentifier.pack(constants.MRD_MESSAGE_ISMRMRD_IMAGE)
                        logging.info("Sending Image")
                        image.serialize_into(self.request.sendall)
                    logging.info("Sending MRD_MESSAGE_CLOSE")
                    self.request.sendall(constants.MrdMessageIdentifier.pack(constants.MRD_MESSAGE_CLOSE))
                    break
                else:
                    logging.warning("Received unsupported message identifier: %d", identifier)
            logging.info("Closing connection")
        except Exception as e:
            logging.error("Error handling connection: %s", e)
        finally:
            logging.info("Closing connection")
            self.request.close()


def main():
    with socketserver.TCPServer(("0.0.0.0", 9002), Server) as server:  # noqa	S104
        logging.info("Starting server...")
        server.serve_forever()


if __name__ == "__main__":
    main()
