#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class Size(int):
	"""Byte size with a human-readable representation"""

	UNITS = {
		"iec": {
			"EiB": 2**60,
			"PiB": 2**50,
			"TiB": 2**40,
			"GiB": 2**30,
			"MiB": 2**20,
			"KiB": 2**10,
		},
		"metric": {
			"EB": 10**18,
			"PB": 10**15,
			"TB": 10**12,
			"GB": 10**9,
			"MB": 10**6,
			"kB": 10**3,
		},
	}

	def __new__(cls, arg: int | float | str) -> Size:
		"""Create Size from int, float, or a string like '1.5GiB' / '10MB' / '10k'"""
		if isinstance(arg, str):
			text = arg.strip().replace(",", ".").replace(" ", "")
			if not text:
				return super().__new__(cls, 0)
			# Bare letter suffix (10G, 10k) → IEC unit
			if text[-1] in "EPTGMk" and not text.lower().endswith(("b", "ib")):
				text += "iB"
			lower = text.lower()
			for unit, value in (cls.UNITS["iec"] | cls.UNITS["metric"]).items():
				if lower.endswith(unit.lower()):
					number = text[: -len(unit)].strip()
					return super().__new__(cls, int(float(number) * value))
			if text[-1] in "bB":
				text = text[:-1]
			arg = text
		return super().__new__(cls, int(arg))

	def __repr__(self) -> str:
		"""IEC and metric forms, e.g. '1.00MiB=1.05MB'"""
		iec = self.string(iec=True)
		metric = self.string(iec=False)
		return iec if iec == metric else f"{iec}={metric}"

	def __str__(self) -> str:
		"""Same as readable representation"""
		return self.__repr__()

	def __add__(self, addend: int) -> Size:
		return Size(int.__add__(self, addend))

	def __radd__(self, addend: int) -> Size:
		return Size(int.__add__(self, addend))

	def __sub__(self, subtrahend: int) -> Size:
		return Size(int.__sub__(self, subtrahend))

	def __rsub__(self, minuend: int) -> Size:
		return Size(int.__sub__(minuend, self))

	def __mul__(self, factor: int) -> Size:
		return Size(int.__mul__(self, factor))

	def __rmul__(self, factor: int) -> Size:
		return Size(int.__mul__(self, factor))

	def __floordiv__(self, quotient: int) -> Size:
		return Size(int.__floordiv__(self, quotient))

	def __truediv__(self, quotient: int) -> Size:
		"""Byte division (floor), keeping Size"""
		return Size(int.__floordiv__(self, quotient))

	def __mod__(self, total: int) -> str:
		"""self as percentage of total, e.g. Size(50) % Size(200) -> '25%'"""
		if not total:
			return "0%"
		return f"{int.__mul__(self, 100).__floordiv__(total)}%"

	def string(self, iec: bool = True, precision: int = 2, delimiter: str = "") -> str:
		"""IEC or metric representation"""
		i = int(self)
		for unit, value in self.UNITS["iec" if iec else "metric"].items():
			if i >= value:
				return f"{i / value:.{precision}f}{delimiter}{unit}"
		return f"{i}B"

	def integer(self) -> int:
		"""Return as plain int"""
		return int(self)
