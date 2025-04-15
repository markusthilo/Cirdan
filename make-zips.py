#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Markus Thilo'
__version__ = '0.9.0.2025-04-15'
__license__ = 'GPL-3'
__email__ = 'markus.thilo@gmail.com'
__status__ = 'Testing'
__description__ = 'Build JSON config files'

COPYTARGET_BASEDIR = '//192.168.128.150/UrkSp/Import'
#UPDATE_DIR = f'{COPYTARGET_BASEDIR}/_dist'
UPDATE_DIR = 'C:/Users/THI/SlowCopy/dist/'	
#MAIL_DIR = '//192.168.128.13/Users/plx-mdsd/POLIKS/EMAIL'
MAIL_DIR = 'C:/Users/THI/Documents/test_mail/'

CONFIGS = (
	# user/department,	target path in import directory,					path to log directory
	('LKA 711',			f'{COPYTARGET_BASEDIR}/LKA 711',					f'{COPYTARGET_BASEDIR}/_logs/LKA 711'),
	('LKA 712',			f'{COPYTARGET_BASEDIR}/LKA 712',					f'{COPYTARGET_BASEDIR}/_logs/LKA 712'),
	('LKA 713',			f'{COPYTARGET_BASEDIR}/LKA 713',					f'{COPYTARGET_BASEDIR}/_logs/LKA 713'),
	('LKA 714',			f'{COPYTARGET_BASEDIR}/LKA 714',					f'{COPYTARGET_BASEDIR}/_logs/LKA 714'),
	('LKA 724',			f'{COPYTARGET_BASEDIR}/LKA 724',					f'{COPYTARGET_BASEDIR}/_logs/LKA 724'),
	('DIR 3 IuK',		f'{COPYTARGET_BASEDIR}/DIR 3',						f'{COPYTARGET_BASEDIR}/_logs/DIR 3'),
	('DIR 4 IuK',		f'{COPYTARGET_BASEDIR}/DIR 4',						f'{COPYTARGET_BASEDIR}/_logs/DIR 4'),
	('DIR 5 IuK',		f'{COPYTARGET_BASEDIR}/DIR 5',						f'{COPYTARGET_BASEDIR}/_logs/DIR 5'),
	('LKA 1 IuK',		f'{COPYTARGET_BASEDIR}/LKA 1',						f'{COPYTARGET_BASEDIR}/_logs/LKA 1'),
	('LKA 2 IuK',		f'{COPYTARGET_BASEDIR}/LKA 2',						f'{COPYTARGET_BASEDIR}/_logs/LKA 2'),
	('LKA 3 IuK',		f'{COPYTARGET_BASEDIR}/LKA 3',						f'{COPYTARGET_BASEDIR}/_logs/LKA 3'),
	('LKA 4 IuK',		f'{COPYTARGET_BASEDIR}/LKA 4',						f'{COPYTARGET_BASEDIR}/_logs/LKA 4'),
	('LKA 5 IuK',		f'{COPYTARGET_BASEDIR}/LKA 5',						f'{COPYTARGET_BASEDIR}/_logs/LKA 5'),
	('LKA 8 IuK',		f'{COPYTARGET_BASEDIR}/LKA 8',						f'{COPYTARGET_BASEDIR}/_logs/LKA 8'),
	('LKA KoSt ST 2',	f'{COPYTARGET_BASEDIR}/LKA KoSt ST 2',				f'{COPYTARGET_BASEDIR}/_logs/LKA KoSt ST 2'),
	#### for test version ####
	#('Test THI':,		f'{COPYTARGET_BASEDIR}/LKA71/SlowCopy_Test_THI',	f'{COPYTARGET_BASEDIR}/LKA71/SlowCopy_Test_THI/_logs')
	('Test THI',			'C:/Users/THI/Documents/test_import/',				'C:/Users/THI/Documents/test_logs/')
)
from pathlib import Path
from json import dump
from zipfile import ZipFile, ZIP_DEFLATED

if __name__ == '__main__':	# start here
	root_path = Path('slowcopy_build')
	for user, target, log in CONFIGS[-3:]:
		with Path('config.json').open('w') as fp:
			dump({'config': {'user': user, 'target': target, 'log': log, 'mail': MAIL_DIR, 'update': UPDATE_DIR}}, fp)


'''		zip_path = Path(f'slowcopy{}.zip')
		with ZipFile(zip_path, 'w', ZIP_DEFLATED) as zf:
			for path in root_path):
				if path.is_dir:
					zf.mkdir(path.relative_to(root_path))
				else:
					zf.write(path, path.relative_to(root_path))

'''