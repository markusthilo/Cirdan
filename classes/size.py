#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class Size(int):
	"""Byte size with "human readable representation"""

	UNITS = {
		"iec": {"EiB": 2**60, "PiB": 2**50, "TiB": 2**40, "GiB": 2**30, "MiB": 2**20, "kiB": 2**10},
		"metric": {"EB": 10**18, "PB": 10**15, "TB": 10**12, "GB": 10**9, "MB": 10**6, "kB": 10**3}
	}

	def __new__(cls, arg: int | str ) -> int:
		"""Create Size from int, str, or Path"""
		if isinstance(arg, str):
			arg = arg.strip().replace(",", ".").replace(" ", "")
			if arg[-1] in "EPTGMk":
				arg += "iB"
			for unit, value in (Size.UNITS["iec"] | Size.UNITS["metric"]).items():
				if arg.lower().endswith(unit.lower()):
					return super().__new__(cls, int(float(arg[:-len(unit)].strip()) * value))
			if arg[-1] in "bB":
				arg = arg[:-1]
		return super().__new__(cls, int(arg))

	def __repr__(self):
		"""Generate readable size"""
		v = list()
		i = int(self)
		for u_dict in self.UNITS.values():
			for unit, value in u_dict.items():
				if i >= value:
					v.append(f"{i/value:.2f}"[:5].rstrip(".") + unit)
					break
		if len(v) < 2:
			v.append(f"{i}B")
		return "=".join(v)

	def __add__(self, addend):
		""" + """
		return Size(int.__add__(self, addend))

	def __sub__(self, subtrahend):
		""" - """
		return Size(int.__sub__(self, subtrahend))

	def __mul__(self, factor):
		""" * """
		return Size(int.__mul__(self, factor))

	def __truediv__(self, quotient):
		""" / """
		return Size(int.__floordiv__(self, quotient))

	def __mod__(self, absolut):
		""" % : Percentage of"""
		return f"{int.__mul__(self, 100).__floordiv__(absolut)}%"

	def string(self, iec=True, precision=2, delimiter=""):
		"""IEC or metric representation"""
		i = int(self)
		for unit, value in self.UNITS['iec' if iec else 'metric'].items():
			if i >= value:
				string = f"{i/value:.{precision}f}"
				return f"{string}{delimiter}{unit}"
		return f"{i}B"

	def integer(self):
		"""Return as int"""
		return int(self)