import numpy as np

from mock import *

from atrcopy import SegmentData, AtariDosDiskImage, Dos33DiskImage,InvalidBinaryFile
from atrcopy.errors import *


class BaseFilesystemModifyTest(object):
    diskimage_type = None
    sample_file = None
    num_files_in_sample = 0

    def setup(self):
        data = np.fromfile(self.sample_file, dtype=np.uint8)
        rawdata = SegmentData(data)
        self.image = self.diskimage_type(rawdata)

    def check_entries(self, entries, prefix="TEST", save=None):
        orig_num_files = len(self.image.files)
        filenames = []
        count = 1
        for data in entries:
            filename = "%s%d.BIN" % (prefix, count)
            self.image.write_file(filename, None, data)
            assert len(self.image.files) == orig_num_files + count
            data2 = np.fromstring(self.image.find_file(filename), dtype=np.uint8)
            assert np.array_equal(data, data2[0:len(data)])
            count += 1

        # loop over them again to make sure data wasn't overwritten
        count = 1
        for data in entries:
            filename = "%s%d.BIN" % (prefix, count)
            data2 = np.fromstring(self.image.find_file(filename), dtype=np.uint8)
            assert np.array_equal(data, data2[0:len(data)])
            count += 1
            filenames.append(filename)

        if save is not None:
            self.image.save(save)

        return filenames

    def test_small(self):
        assert len(self.image.files) == self.num_files_in_sample

        data = np.asarray([0xff, 0xff, 0x00, 0x60, 0x01, 0x60, 1, 2], dtype=np.uint8)
        self.image.write_file("TEST.XEX", None, data)
        assert len(self.image.files) == self.num_files_in_sample + 1

        data2 = np.fromstring(self.image.find_file("TEST.XEX"), dtype=np.uint8)
        assert np.array_equal(data, data2[0:len(data)])

    def test_50k(self):
        assert len(self.image.files) == self.num_files_in_sample

        data = np.arange(50*1024, dtype=np.uint8)
        self.image.write_file("RAMP50K.BIN", None, data)
        assert len(self.image.files) == self.num_files_in_sample + 1

        data2 = self.image.find_file("RAMP50K.BIN")
        assert data.tostring() == data2

    def test_many_small(self):
        entries = [
            np.asarray([0xff, 0xff, 0x00, 0x60, 0x01, 0x60, 1, 2], dtype=np.uint8),
            np.arange(1*1024, dtype=np.uint8),
            np.arange(2*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(4*1024, dtype=np.uint8),
            np.arange(5*1024, dtype=np.uint8),
            np.arange(6*1024, dtype=np.uint8),
            np.arange(7*1024, dtype=np.uint8),
            np.arange(8*1024, dtype=np.uint8),
            np.arange(9*1024, dtype=np.uint8),
            np.arange(10*1024, dtype=np.uint8),
            ]
        self.check_entries(entries, save="many_small.atr")

    def test_big_failure(self):
        assert len(self.image.files) == self.num_files_in_sample

        data = np.arange(50*1024, dtype=np.uint8)
        self.image.write_file("RAMP50K.BIN", None, data)
        assert len(self.image.files) == self.num_files_in_sample + 1
        with pytest.raises(NotEnoughSpaceOnDisk):
            self.image.write_file("RAMP50K2.BIN", None, data)
        assert len(self.image.files) == self.num_files_in_sample + 1

    def test_delete(self):
        entries1 = [
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(10*1024, dtype=np.uint8),
            np.arange(10*1024, dtype=np.uint8),
            ]
        entries2 = [
            np.arange(10*1024, dtype=np.uint8),
            np.arange(5*1024, dtype=np.uint8),
        ]
        
        filenames = self.check_entries(entries1, "FIRST")
        assert len(self.image.files) == self.num_files_in_sample + 11
        self.image.delete_file(filenames[2])
        self.image.delete_file(filenames[5])
        self.image.delete_file(filenames[0])
        self.image.delete_file(filenames[8])
        assert len(self.image.files) == self.num_files_in_sample + 7

        filename = self.check_entries(entries2, "SECOND", save="test_delete.atr")
        assert len(self.image.files) == self.num_files_in_sample + 9

    def test_delete_all(self):
        entries1 = [
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(3*1024, dtype=np.uint8),
            np.arange(10*1024, dtype=np.uint8),
            np.arange(11*1024, dtype=np.uint8),
            np.arange(12*1024, dtype=np.uint8),
        ]
        for dirent in self.image.files:
            self.image.delete_file(dirent.filename)
        assert len(self.image.files) == 0

class TestAtariDosSDImage(BaseFilesystemModifyTest):
    diskimage_type = AtariDosDiskImage
    sample_file = "../test_data/dos_sd_test1.atr"
    num_files_in_sample = 5

class TestDos33Image(BaseFilesystemModifyTest):
    diskimage_type = Dos33DiskImage
    sample_file = "../test_data/dos33_master.dsk"
    num_files_in_sample = 19


if __name__ == "__main__":
    t = TestAtariDosFile()
    t.setup()
    t.test_segment()