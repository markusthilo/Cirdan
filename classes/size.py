#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class Size(int):
	'''Bytes using int'''

	def __add__(self, value):
		'''Add two Size objects'''
		return Size(int.__add__(self, value))

	def readable(self, fmt='{iec} = {si}'):
		'''Genereate readable size string,
			format_k: "{iec} / {si} / {b} B" gives e.g. 9.54 MiB / 10.0 MB / 10000000 B
			"{b} B" will be returned if size < 1024 bytes
		'''
		try:
			size = int(self)
		except:
			return '#####'
		if size < 0:
			return '-----'
		if size < 1024:
			return f'{size} B'
		iec = None
		rnd_iec = 0
		si = None
		rnd_si = 0
		def _round(*base):	# intern function to calculate human readable
			for prefix, b in base:
				rnd = round(self/b, 2)
				if rnd >= 1:
					break
			if rnd >= 10:
				rnd = round(rnd, 1)
			if rnd >= 100:
				rnd = round(rnd)
			return f'{rnd} {prefix}', rnd	# end if intern function
		if '{iec}' in fmt:
			iec, rnd_iec = _round(('PiB', 2**50), ('TiB', 2**40), ('GiB', 2**30), ('MiB', 2**20), ('kiB', 2**10))
		if '{si}' in fmt:
			si, rnd_si = _round(('PB', 10**15), ('TB', 10**12), ('GB', 10**9), ('MB', 10**6), ('kB', 10**3))
		return fmt.format(iec=iec, si=si, b=size)
