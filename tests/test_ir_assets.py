import pytest
from threatresponse import app
from threatresponse import ir_assets

asset = ir_assets.IR_Asset()
asset.case_number = "cr-9999999999999999999999999999999999999"

def test_case_number_not_null():
    assert asset.case_number is not None

def test_set_case_bucket():
    assert asset.bucket is not None

def test_logfiles():
    logfiles = ir_assets.LogFile()
    l = logfiles.generate_filename('console-log', 'i-32bfa0a7')
    assert l is not None
