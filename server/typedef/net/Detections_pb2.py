# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: Detections.proto
# Protobuf Python Version: 4.25.2
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x10\x44\x65tections.proto\"0\n\rTranslation3d\x12\t\n\x01x\x18\x01 \x01(\x01\x12\t\n\x01y\x18\x02 \x01(\x01\x12\t\n\x01z\x18\x03 \x01(\x01\"\x92\x01\n\tDetection\x12\x11\n\ttimestamp\x18\x01 \x01(\x03\x12\x10\n\x08label_id\x18\x02 \x01(\x05\x12\x12\n\nconfidence\x18\x03 \x01(\x01\x12%\n\rpositionRobot\x18\x04 \x01(\x0b\x32\x0e.Translation3d\x12%\n\rpositionField\x18\x05 \x01(\x0b\x32\x0e.Translation3d\"<\n\nDetections\x12\x0e\n\x06labels\x18\x01 \x03(\t\x12\x1e\n\ndetections\x18\x02 \x03(\x0b\x32\n.Detectionb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'Detections_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_TRANSLATION3D']._serialized_start=20
  _globals['_TRANSLATION3D']._serialized_end=68
  _globals['_DETECTION']._serialized_start=71
  _globals['_DETECTION']._serialized_end=217
  _globals['_DETECTIONS']._serialized_start=219
  _globals['_DETECTIONS']._serialized_end=279
# @@protoc_insertion_point(module_scope)