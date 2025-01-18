"""Constants in MRD Protocol"""

import struct

# Message Types
MRD_MESSAGE_CONFIG_FILE = 1
MRD_MESSAGE_CONFIG_TEXT = 2
MRD_MESSAGE_METADATA_XML_TEXT = 3
MRD_MESSAGE_CLOSE = 4
MRD_MESSAGE_TEXT = 5
MRD_MESSAGE_ISMRMRD_ACQUISITION = 1008
MRD_MESSAGE_ISMRMRD_IMAGE = 1022
MRD_MESSAGE_ISMRMRD_WAVEFORM = 1026

# Message Fields
MrdMessageLength = struct.Struct("<I")
SIZEOF_MRD_MESSAGE_LENGTH = len(MrdMessageLength.pack(0))

MrdMessageIdentifier = struct.Struct("<H")
SIZEOF_MRD_MESSAGE_IDENTIFIER = len(MrdMessageIdentifier.pack(0))

MrdMessageConfigurationFile = struct.Struct("<1024s")
SIZEOF_MRD_MESSAGE_CONFIGURATION_FILE = len(MrdMessageConfigurationFile.pack(b""))

MrdMessageAttribLength = struct.Struct("<Q")
SIZEOF_MRD_MESSAGE_ATTRIB_LENGTH = len(MrdMessageAttribLength.pack(0))

# Accepted Data Types
DATATYPE_USHORT = 1  # corresponds to uint16
DATATYPE_SHORT = 2  # corresponds to int16
DATATYPE_FLOAT = 5  # corresponds to float32
DATATYPE_CXFLOAT = 7  # corresponds to complex64

# ISMRM Image Types
IMTYPE_MAGNITUDE = 1
IMTYPE_PHASE = 2
IMTYPE_REAL = 3
IMTYPE_IMAG = 4
IMTYPE_COMPLEX = 5
