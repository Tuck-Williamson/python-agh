import tempfile
import unittest
from dataclasses import dataclass, asdict, field
from pathlib import Path

from agh.agh_data import DataclassJson


@dataclass(kw_only=True)
class CheckDataclass(DataclassJson):
  a : int = 1
  b : str = "2"


@dataclass(kw_only=True)
class CheckDataclass2(DataclassJson):
  a : CheckDataclass
  b : str = "2"


@dataclass(kw_only=True)
class CheckDataclass3(DataclassJson):
  a : CheckDataclass2


@dataclass(kw_only=True)
class CheckDataclass4(DataclassJson):
  a : list[CheckDataclass] = field(default_factory=list)

@dataclass(kw_only=True)
class CheckDataclass5(DataclassJson):
  a : dict[str, CheckDataclass] = field(default_factory=dict)


class TestDataclassJson(unittest.TestCase):

  def test_to_dict(self):
    tdclass = CheckDataclass(a=12, b='12')
    self.assertEqual(asdict(tdclass), {'a': 12, 'b': '12'})
  def test_save_load(self):
    tdclass = CheckDataclass(a=12, b='12')
    with tempfile.TemporaryDirectory() as td:
      fs = Path(td) / "test.json"
      tdclass.save(fs)
      tdc2 = CheckDataclass.load_json(fs)
      self.assertEqual(tdc2, tdclass)
      self.assertEqual(asdict(tdclass), {'a': 12, 'b': '12'})
  def test_nested_save_load(self):
    tdclass = CheckDataclass2(a=CheckDataclass(a=5, b='5'))
    self.assertEqual(asdict(tdclass), {'a': {'a': 5, 'b': '5'}, 'b': '2'})
    with tempfile.TemporaryDirectory() as td:
      fs = Path(td) / "test.json"
      tdclass.save(fs)
      tdc2 = CheckDataclass2.load_json(fs)
      self.assertEqual(tdc2, tdclass)
      self.assertEqual(asdict(tdc2), {'a': {'a': 5, 'b': '5'}, 'b': '2'})
  def test_nested_list_save_load(self):
    tdclass = CheckDataclass4(a=[CheckDataclass(a=5, b='5'), CheckDataclass(a=4, b='4')])
    check_val = {'a': [{'a': 5, 'b': '5'}, {'a': 4, 'b': '4'}]}
    self.assertEqual(asdict(tdclass), check_val)
    with tempfile.TemporaryDirectory() as td:
      fs = Path(td) / "test.json"
      tdclass.save(fs)
      tdc2 = CheckDataclass4.load_json(fs)
      self.assertEqual(tdc2, tdclass)
      self.assertEqual(asdict(tdc2), check_val)
  def test_double_nested_list_save_load(self):
    tdclass = CheckDataclass3(a=CheckDataclass2(a=CheckDataclass(a=5, b='5')))
    check_val = {'a': {'a': {'a': 5, 'b': '5'}, 'b': '2'}}
    self.assertEqual(asdict(tdclass), check_val)
    with tempfile.TemporaryDirectory() as td:
      fs = Path(td) / "test.json"
      tdclass.save(fs)
      tdc2 = CheckDataclass3.load_json(fs)
      self.assertEqual(tdc2, tdclass)
      self.assertEqual(asdict(tdc2), check_val)
  def test_nested_dict_save_load(self):
    tdclass = CheckDataclass5(a={'1': CheckDataclass(a=5, b='5'), '2': CheckDataclass(a=4, b='4')})
    check_val = {'a': {'1': {'a': 5, 'b': '5'}, "2": {'a': 4, 'b': '4'}}}
    self.assertEqual(asdict(tdclass), check_val)
    with tempfile.TemporaryDirectory() as td:
      fs = Path(td) / "test.json"
      tdclass.save(fs)
      tdc2 = CheckDataclass5.load_json(fs)
      self.assertEqual(tdc2, tdclass)
      self.assertEqual(asdict(tdc2), check_val)
