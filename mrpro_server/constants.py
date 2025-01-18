import struct

MRD_MESSAGE_CONFIG_FILE = 1
MRD_MESSAGE_CONFIG_TEXT = 2
MRD_MESSAGE_METADATA_XML_TEXT = 3
MRD_MESSAGE_CLOSE = 4
MRD_MESSAGE_TEXT = 5
MRD_MESSAGE_ISMRMRD_ACQUISITION = 1008
MRD_MESSAGE_ISMRMRD_IMAGE = 1022
MRD_MESSAGE_ISMRMRD_WAVEFORM = 1026

MrdMessageLength = struct.Struct("<I")
SIZEOF_MRD_MESSAGE_LENGTH = len(MrdMessageLength.pack(0))

MrdMessageIdentifier = struct.Struct("<H")
SIZEOF_MRD_MESSAGE_IDENTIFIER = len(MrdMessageIdentifier.pack(0))

MrdMessageConfigurationFile = struct.Struct("<1024s")
SIZEOF_MRD_MESSAGE_CONFIGURATION_FILE = len(MrdMessageConfigurationFile.pack(b""))

MrdMessageAttribLength = struct.Struct("<Q")
SIZEOF_MRD_MESSAGE_ATTRIB_LENGTH = len(MrdMessageAttribLength.pack(0))

DATATYPE_INT = 4  # corresponds to int32
DATATYPE_FLOAT = 5  # corresponds to float32
DATATYPE_DOUBLE = 6  # corresponds to float64
DATATYPE_CXFLOAT = 7  # corresponds to complex64
DATATYPE_CXDOUBLE = 8  # corresponds to complex128
