
__author__  = 'Aaron Gudmundson'
__email__   = 'agudmun2@jhmi.edu'
__date__    = '2023/06/01'


# from fpdf import FPDF
from tkinter import filedialog 														# File Explorer through Tkinter
import tkinter as tk     															# Graphical User Interface
import pandas as pd 																# DataFrames
import numpy as np  																# Arrays
import time as t0 																	# Timer
import subprocess 																	# Running Terminal Commands
import logging 																		# Log File
import shutil 																		# Copy, Move, "which $program"
import copy  																		# Copying Objects
import glob 																		# Bash-like File Calls
import sys 																			# Interact with System
import re  																			# Regular Expressions 
import os																			# Interact with Operating System


def setup_log(log_name, log_file, level=logging.INFO): 								# Create new global log file
	'''
	- 1. Description:
		- Creates logfile
	
	- 2. Inputs:
		- log_name : (String) Name of the log 
		- log_file : (String) Filename of the log
		- level    : (Func  ) Level to log (default to debug and info)

	- 3. Outputs:
		- logger   : (Logger) Global log object
	'''

	formatter = logging.Formatter('(%(asctime)s) %(message)s'       , 				# Logging format (Time and Message)
								  datefmt = '%m/%d/%Y %I:%M:%S %p') 				# Date/Time Specific Formatting
	
	handler = logging.FileHandler(log_file)         								# Log Handler
	handler.setFormatter(formatter)													# Log Formatting

	logger  = logging.getLogger(log_name) 											# Instantiate Logger
	logger.setLevel(level) 															# Set Log Level
	logger.addHandler(handler) 														# Connect Handler

	return logger 																	# Return Logger Object

def write_log(log, message): 														# Log Writing
	if log != None: 																# Check Log is set to Write
		try:
			long_spc = (' '*36)
			message  = message.replace('\n\t', '\n{}'.format(long_spc)) 			# Add Long Space to Newlines for alignment 
		except Exception as e:
			print('Write Log Error: {}'.format(e))
		log.info(message) 															# Log - 
	# else: 																		# Log Write is set to No
	# 	print('Not writing: {}'.format(message)) 									# Logging is Turned off

class Application(tk.Tk): 															# Create Application Class
	def __init__(self, lwrite=True): 												# Init
		super().__init__() 															# Initialize tk.Tk

		userwidth  = self.winfo_screenwidth() 										# User's Screen Width
		userheight = self.winfo_screenheight() 										# User's Screen Height

		width      = int(userwidth * 0.30) 											# Application Width
		height     = int(userwidth * 0.20) 											# Application Height

		# print('User Width : {}'.format(userwidth))									#
		# print('User Height: {}'.format(userheight))									#
		# print(' ')																	#
		# print('Width      : {}'.format(width))										#
		# print('Height     : {}'.format(height))										#
		# print(' ')																	#


		## Main Window Control 														
		# self.geometry('{}x{}'.format(width, height))								# Geometry Width x Height
		self.minsize(width, height) 												# Screen can't be smaller
		self.config(bg='white') 													# Set Background White


		## Required Classes, Functions, etc.													
		self.Table   = Table() 														# MRSinMRS Table Creation
		self.DRead   = DataReaders() 												# Vendor Data Readers
		self.lwrite  = lwrite  														# Write to Log File
		self.exe 	 = bool  														# Executable or CommandLine


		## Window Label
		self.title('Reproducibility Made Easy') 									# Label The Application Window


		## This is the primary Grid Layout Frame
		self.frame  = tk.Frame(self, borderwidth=10)# , width=width, height=height)
		self.frame.grid(row=0, column=0, columnspan=2, rowspan=10, sticky=tk.W+tk.E+tk.N+tk.S)
		self.frame.config(bg='white')
		self.frame.pack(pady=5, padx=5)


		## Primary Label (at Top)
		prim_label      = '  \n'
		prim_label      = 'Reproducibility Made Easy\n'.format(prim_label)
		self.prim_label = tk.Label(self.frame, text='Reproducibility Made Easy')
		self.prim_label.config(font=('Arial', 20, 'bold'), bg='royalblue')
		self.prim_label.grid(row=0, column=0, rowspan=1, columnspan=2, sticky=tk.W+tk.E+tk.N+tk.S)


		## Reproducibility Made Easy Description
		desc_label       = ''
		desc_label       = '{}Export a CSV File according to the '.format(desc_label)
		desc_label       = '{}MRSinMRS guidelines using MRS files headers\n'.format(desc_label)
		self.desc_label = tk.Label(self.frame, text=desc_label)
		self.desc_label.config(font=('Arial', 16), bg='royalblue')
		self.desc_label.grid(row=4, column=0, rowspan=1, columnspan=2, sticky=tk.W+tk.E+tk.N+tk.S)


		## Reproducibility Made Easy Team
		RME_label       = ''
		RME_label       = '{}Reproducibility Made Easy Team:\n'.format(RME_label)
		RME_label       = '{}Antonia Susjnar, Antonia Kaiser, Gianna Nossa, '.format(RME_label)
		RME_label       = '{}Dunja Simicic, and\nAaron Gudmundson\n\n'.format(RME_label)
		self.RME_label = tk.Label(self.frame, text=RME_label)
		self.RME_label.config(font=('Arial',14), bg='white')
		self.RME_label.grid(row=5, column=0, rowspan=1, columnspan=2, sticky=tk.W+tk.E+tk.N+tk.S)
		# self.RME_label.pack(pady=0)

 
		## MRSinMRS Citation
		cite_names      = ''
		cite_names      = '{}Lin A, Andronesi O, Bogner W, et al.\n'.format(cite_names)
		cite_names      = '{}Minimum Reporting Standards for in vivo Magnetic '.format(cite_names)
		cite_names      = '{}Resonance Spectroscopy (MRSinMRS):\n'.format(cite_names)
		cite_names      = '{}Experts’ consensus recommendations. NMR in Biomedicine. '.format(cite_names)
		cite_names      = '{}2021;34(5). doi:10.1002/nbm.4484\n\n'.format(cite_names)
		self.citation   = tk.Label(self.frame, text=cite_names)
		self.citation.config(font=('Arial', 12), bg='white')
		self.citation.grid(row=6, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
		# self.citation.pack(pady=0)


		## Main Button Box
		self.button_frame      = tk.Frame(self.frame, borderwidth=5)
		self.button_frame.grid(row=7, column=0, columnspan=2, rowspan=2, sticky=tk.W+tk.E+tk.N+tk.S)
		self.button_frame.config(bg='white')


		## Determine if running in application or 
		if getattr(sys, 'frozen', False): 													# Determine if Application or CommandLine
			print('Running inside executable...')
			self.cwd = os.path.abspath(os.path.dirname(__file__))
			self.exe = True 																# Note
		elif __file__: 																		# Command Line
			self.cwd = os.path.dirname(os.path.realpath(__file__)) 							# Command Line - Set Directory
			self.exe = False 																# Note  
		self.cwd = self.cwd.replace('\\', '/') 												# Remove any Windows' backslashes


		## File Import Button
		self.import_button = tk.Button(self.button_frame, text='Import', width=15, height=2, command=self.import_file)
		self.import_button.grid(row=0, column=0)
		self.import_label  = tk.Label(self.button_frame, text=self.cwd)
		self.import_label.config(font=('Arial', 14), bg='white')
		self.import_label.grid(row=0, column=1, sticky=tk.W+tk.E+tk.N+tk.S)


		## File Export Button
		self.export_button = tk.Button(self.button_frame, text='Export', width=15, height=2, command=self.export_file)
		self.export_button.grid(row=1, column=0)
		self.export_label  = tk.Label(self.button_frame, text=self.cwd)
		self.export_label.config(font=('Arial', 14), bg='white')
		self.export_label.grid(row=1, column=1, sticky=tk.W+tk.E+tk.N+tk.S)  


		## Button Commands
		self.command_frame = tk.Frame(self.frame, borderwidth=5)
		self.command_frame.grid(row=9, column=0, columnspan=2)
		self.command_frame.config(bg='white')


		## User Data Selections - Vendor
		self.vendor     = tk.StringVar()
		self.vendor.set('Select Vendor')
		self.vendor_opt = ['Siemens', 'Philips', 'GE', 'Bruker']
		self.command_01 = tk.OptionMenu(self.command_frame, self.vendor, *self.vendor_opt, command=self.command_button_01)
		self.command_01.config(height=2, width=30)
		self.command_01.grid(row=0, column=1, sticky=tk.W+tk.E+tk.N+tk.S)


		## User Data Selections - DataType
		self.dtype     = tk.StringVar()
		self.dtype.set('First Select Vendor')
		self.dtype_opt = ['Siemens TWIX (.dat)' ,  											# Siemens Twix  (.dat)
						  'Siemens Dicom (.ima)',  											# Siemens Dicom (.ima)
						  'Philips (.spar)'     ,  											# Philips SPAR  (.sdat or .data/.list)
						  'GE (.7)'             ,  											# GE      Pfile (.7)
						  'Bruker (method)'     ,  											# Bruker  method
						  'Bruker (2dseq)'      ]  											# Bruker  2dseq
		self.command_02 = tk.OptionMenu(self.command_frame, self.dtype, *self.dtype_opt, command=self.command_button_02)
		self.command_02.config(height=2, width=30)
		self.command_02.grid(row=0, column=2, sticky=tk.W+tk.E+tk.N+tk.S)


		## Instantiate Vendor and Dtype
		self.vendor_selection = ''
		self.dtype_selection  = ''


		## Button Commands
		self.run_frame = tk.Frame(self.frame, borderwidth=5)
		self.run_frame.grid(row=10, column=0, columnspan=2, rowspan=1)
		self.run_frame.config(bg='white')


		## Run Script
		self.command_03 = tk.Button(self.run_frame, text='Run', width = 30, command=self.command_button_03)
		self.command_03.config(height=2, width=60)
		self.command_03.grid(row=0, column=5, sticky=tk.W+tk.E+tk.N+tk.S)
		self.update()


	## Import Button Function
	def import_file(self):
		filepath = filedialog.askopenfilename()  											# Open File Explorer
		filepath = filepath.replace('\\', '/') 												# Replace any Windows' backslashes

		filepath = (filepath.replace('.SDAT', '.SPAR') if '.SDAT' in filepath else  		# Must be .spar - User gave .sdat
					filepath.replace('.sdat', '.spar'))
		filepath = (filepath.replace('.DATA', '.SPAR') if '.DATA' in filepath else   		# Must be .spar - User gave .data
					filepath.replace('.data', '.spar'))
		filepath = (filepath.replace('.LIST', '.SPAR') if '.LIST' in filepath else   		# Must be .spar - User gave .list
					filepath.replace('.list', '.spar'))


		if os.path.exists(filepath): 														# Ensure Path Exists
			self.import_fpath = copy.deepcopy(filepath) 									# Import Path
			self.export_fpath = os.path.dirname(filepath)
			exp_fpath         = copy.deepcopy(self.export_fpath)

			if len(filepath) > 60:
				self.import_label['text'] = (  filepath[:30 ] + ' ... '  
				 							 + filepath[-30:]        ) 						# Shorten Import Path Display

				self.export_label['text'] = (  exp_fpath[:30 ] + ' ... '  
				 							 + exp_fpath[-30:]        ) 					# Shorten Import Path Display

			else:
				self.export_fpath         = copy.deepcopy(exp_fpath)
				self.import_label['text'] = filepath				 						# Display Import Path
				self.import_label['text'] = filepath				 						# Display Import Path
				# self.export_label['text'] = '{}_MRSinMRS.csv'.format(filepath.split('.')[0])# Display Updated Expport Path

			self.command_03['text'] = 'Run' 												# Update Text
			print('Import file:', filepath) 												# 

	## Export Button Function
	def export_file(self):
		filepath = filedialog.askdirectory() 												# Open File Explorer
		filepath = filepath.replace('\\', '/') 												# Replace any Windows' backslashes

		if os.path.exists(filepath):
			self.export_fpath         = copy.deepcopy(filepath) 							# Export Path
		
			if len(filepath) > 60: 															# Export Path is Long
				self.export_label['text'] = (  filepath[ :30] + '...'  						# 
				 							 + filepath[-30:]        ) 						# Shorten Export Path Display
			else:
				self.export_label['text'] = filepath 										# Display Full Export Path

		print('Export file:', filepath)														# 


	## Vendor Selection Button Function
	def command_button_01(self, selection):
		print('Selected: ', selection) 														# User Selected Vendor  
		
		self.vendor_selection = selection

		if selection.lower() == 'siemens': 													# Siemens
			self.dtype.set('{}: Select Twix (.dat) or Dicom (.ima)'.format(selection)) 		# Twix

		elif selection.lower() == 'philips': 												# Philips
			self.dtype.set('{}: Select (.spar) for .sdat or raw data'.format(selection)) 	# SDAT/SPAR and Data/List

		elif selection.lower() == 'ge': 													# GE
			self.dtype.set('{}: Select Pfile (.7)'.format(selection))						# PFile

		elif selection.lower() == 'bruker': 												# Bruker
			self.dtype.set('{}: Select (method OR 2dseq)'.format(selection))				# 2dseq


	## Datatype Selection Button Function
	def command_button_02(self, selection):
		print('Selected: ', selection) 														# User Selected Datatype        

															 								# Vendor Matched to avoid misclicks
		vendor_dtypes = {'siemens': ['Siemens TWIX (.dat)'  , 								# Siemens Twix .dat
									 'Siemens Dicom (.ima)' ], 								# Siemens Dicom .ima
						 'philips': ['Philips (.spar)'      ],								# Philips sdat/spar or data/list
						 'ge'     : ['GE (.7)'              ], 								# GE Pfile
						 'bruker' : ['Bruker (method)'      , 								# Bruker Method File
						 			 'Bruker (2dseq)'       ]} 								# Bruker 2dseq
		
		vendor_dtypes = vendor_dtypes[self.vendor_selection.lower()] 						# Current Vendor Datatypes

		if selection not in vendor_dtypes: 													# User accidentally selected wrong datatype
			self.command_03['text'] = 'Please Select Appropriate Datatype' 					# Update Text
			return

		self.dtype_selection = selection 													# Datatype Selection
		self.dtype.set(selection) 															# Set the Datatype Text Display

		self.dtype_selection = self.dtype_selection.lower()  								# Lowercase
		self.dtype_selection = self.dtype_selection.split('(')[1] 							# Split off filetype
		self.dtype_selection = self.dtype_selection.split(')')[0] 							# Split off filetype
		self.dtype_selection = self.dtype_selection.replace('/', '_') 						# Remove / if spar/sdat 
		self.dtype_selection = self.dtype_selection.replace('.', '') 						# Remove any period preceding extension

	## Running the Script Button
	def command_button_03(self):

		self.command_03['text'] = 'Running...' 												# Update Text

		## Update Button Selections
		possible_vendors = ['siemens', 'philips', 'ge', 'bruker'] 							# Currently Supported Vendors 
		if self.vendor_selection.lower() not in possible_vendors: 							# User dit not Select Supported Vendors 
			self.command_03['text'] = 'Please select Vendor and Datatype' 					# Update Text
			return

		possible_dtypes  = ['spar', 'dat', '7', 'method', '2dseq']							# Currently Supported Datatypes 
		if self.dtype_selection.lower()  not in possible_dtypes:							# User did not Select Supported Datatypes
			self.command_03['text'] = 'Please select Datatype' 								# Update Text
			return


		## Filenames
		if os.path.isdir(self.export_fpath): 												# Determine if Path or .csv
			pname = self.export_fpath 														# Selected Path Name
		else:
			pname = os.path.dirname(self.export_fpath) 										# Selected Path Name

		iname = self.import_fpath[:].split('/')[-1] 										# Get the Filename
		fname = self.import_fpath[:].split('/')[-1] 										# Get the Filename

		oname = '' 																			# This will be the Output file name
		if len(fname.split('.')[0]) == 2: 													# Ensure user doesn't include . in filename
			oname = fname.split('.')[0] 	 												# Remove file extension
		else:  																				# User includes . in filename
			fname_ = fname.split('.')[:-1] 													# Remove extension
			for ii in range(len(fname_)): 													# Iterate back through fname pieces
				oname = '{}{}'.format(oname, fname_[ii]) 									# Recombine into oname


		## Setup Log File
		if self.lwrite: 																	# Create a Logfile
			log = setup_log(oname, '{}/{}_Log.log'.format(pname, oname)) 					# Log File
		else:
			log = None 																		# User Selected Not to Create Log File


		## Begin Writing Log File 
		write_log(log, ' ') 																# Log - Intentional Empty Line
		write_log(log, '--'*30)  															# Log - Dashed Line to Separate Entries
		write_log(log, 'Reproducibility Made Easy is Starting..') 							# Log - Reproducibility Made Easy

		if self.exe == True:
			write_log(log, 'Software Running with Application') 							# Log - Running from Application
			write_log(log, 'Software Directory: {}'.format(self.cwd)) 						# Log - Running from Application
		else:
			write_log(log, 'Software Running from Command Line') 							# Log - Running from the Command Line
			write_log(log, 'Software Directory: {}'.format(self.cwd)) 						# Log - Running from Application

		write_log(log, ' ') 																# Log - Intentional Empty Line
		write_log(log, 'Base Dir : {}'.format(pname))  										# Log - Base Directory
		write_log(log, 'Filename : {}'.format(iname))										# Log - Filename
		write_log(log, 'Out Dir  : {}'.format(pname))										# Log - Export Directory
		write_log(log, 'Out Name : {}.csv'.format(oname))									# Log - Export Filename (without extension)
		write_log(log, 'Vendor   : {}'.format(self.vendor_selection)) 						# Log - Vendor Selected
		write_log(log, 'Datatype : {}\n'.format(self.dtype_selection)) 						# Log - Datatype Selected


		## Data Read using Spec2nii
		write_log(log, 'Data Read: ') 														# Log - Intentional Empty Line
		write_log(log, 'Data Read: Starting Data Read using spec2nii')  					# Log - Failed to Read Data
		if (    (self.exe == False and isinstance(shutil.which('spec2nii'), str) == True) 	# spec2nii at command line
		     or (self.exe == True)): 														# spec2nii from executable
			write_log(log, 'Data Read: spec2nii is installed'             +					# Log - Successfully Read Data
						   '\n\tNote** The Application version of '  	  +	
						   'Reproducibility Made Easy comes with spec2nii'+
						   ' installed.\n\tThis is intentional to make '  + 
						   'this product usable for anyone\n\tHowever, '  +
						   'this means the downloaded version may become '+
						   'outdated...\n\tWe recommend re-installing '   +
						   'if experiencing problems' 					  )

			try: 																			# Try using spec2nii to Read Data
				import_text  = self.import_fpath
				if self.vendor_selection.lower() == 'siemens': 								# Siemens
					if self.dtype_selection == 'dat': 										# Brukler Data Reader from Method file
						write_log(log, 'Data Read: Siemens Twix uses pyMapVBVD ')			# Log - pyMapVBVD
						MRSinMRS, log = self.DRead.siemens_twix(import_text, log) 			# Siemens Data Reader from mapVBVD

					if self.dtype_selection == 'ima': 										# Brukler Data Reader from Method file
						write_log(log, 'Data Read: Siemens Dicom uses pydicom ')			# Log - pyDicom
						MRSinMRS, log = self.DRead.siemens_ima(import_text, log) 			# Siemens Data Reader from mapVBVD

				elif self.vendor_selection.lower() == 'philips': 							# Philips 
					MRSinMRS, log = self.DRead.philips_spar(import_text, log)				# Philips .spar Reader from spec2nii
					
				elif self.vendor_selection.lower() == 'ge': 								# GE
					MRSinMRS, log = self.DRead.ge_7(import_text, log) 						# GE Data Reader from spec2nii

				elif self.vendor_selection.lower() == 'bruker': 							# Bruker
					if self.dtype_selection == 'method': 									# Brukler Data Reader from Method file
						MRSinMRS, log = self.DRead.bruker_2dseq(import_text, log) 			# Brukler Data Reader from Method file
					
					elif self.dtype_selection == '2dseq':
						write_log(log, 'Data Read: Bruker uses BrukerAPI '    + 			# Log - BrukerAPI
									   'developed by Tomáš Pšorn\n\t'         +				# Log - BrukerAPI Creator
									   'github.com/isi-nmr/brukerapi-python'  )				# Log - BrukerAPI Address
						MRSinMRS, log = self.DRead.bruker_2dseq(import_text, log) 			# Brukler Data Reader from BrukerAPI

				write_log(log, 'Data Read: Completed\n') 									# Log - Successfully Read Data

			except Exception as e: 															# Data Reader Failed
				write_log(log, 'Data Read: Failed ** **')  									# Log - Failed to Read Data
				write_log(log, 'Data Read: Error - {}\n'.format(e))  						# Log - Error

		else:
			d1 = 'aarongudmundsonphd@gmail.com'  											# Aaron Gudmundson, PhD
			d2 = 'antonia.kaiser@epfl.ch'  													# Antonia Kaiser, PhD
			d3 = 'asusnjar@mgh.harvard.edu'  												# Antonia Susjnar, PhD
			write_log(log, 'spec2nii : spec2nii was not found..'          + 				# Log - Successfully Read Data
						   '\n\tNote** The Application version of '  	  +	
						   'Reproducibility Made Easy comes with spec2nii'+
						   ' installed.\n\tHowever, it is not being '     +
						   'located during runtime..\n\tPlease contact '  +
						   'the developers:'             				  +
						   '\n\t\t{}\n\t\t{}\n\t\t{}'.format(d1, d2, d3)  )


		write_log(log, 'Table    :') 																# Log - 
		## Check for Missing MRSinMRS Values that might have different names across versions
		try:
			MRSinMRS = self.Table.table_clean(self.vendor_selection, self.dtype_selection, MRSinMRS)
			write_log(log, 'Table    : table_clean Successful') 							# Log - Failed to Populate Table
		except Exception as e:
			write_log(log, 'Table    : table_clean Failed') 								# Log - Failed to Populate Table
			write_log(log, 'Table    : table_clean Error - {}'.format(e))  					# Log - Error


		## Populate MRS Table
		try:
			self.Table.populate(self.vendor_selection, self.dtype_selection, MRSinMRS)
			write_log(log, 'Table    : populate table Successful') 							# Log - Successfully Populated Table
		except Exception as e:
			write_log(log, 'Table    : populate table Failed') 								# Log - Failed to Populate Table
			write_log(log, 'Table    : populate table Error - {}'.format(e))  				# Log - Error


		## Export Table as .csv
		csvname = '{}/{}_Table.csv'.format(pname, oname) 									# Name of .csv file
		csvcols = ['Header', 'SubHeader', 'MRSinMRS', 'Values'] 							# Columns to Include in Output .csv

		self.Table.MRSinMRS_Table[csvcols].to_csv(csvname) 									# Create .csv
		write_log(log, 'Table    : Created MRSinMRS Table as .csv file\n') 					# Log - Failed to Populate Table


		## Export LaTeX .pdf
		write_log(log, 'LaTeX PDF: ') 														# Log - Intentional Empty Line
		write_log(log, 'LaTeX PDF: Starting LaTeX to PDF') 									# Log - Starting LaTeX
		try:

			LaTeX_dir   = '{}/LaTeX_Extras'.format(pname) 									# LaTeX Extras Directory Name
			os.mkdir(LaTeX_dir) 	 														# Store all the LaTeX Files									

			## LaTeX File
			latex_name  = '{}/{}.tex'.format(LaTeX_dir, oname) 								# LaTeX Filename
			latex_content,errors = self.Table.table_to_latex() 								# Read LaTeX Template
			if len(errors) > 1:
				write_log(log, 'LaTeX PDF: Replaced LaTeX Content w/Errors:') 				# Log - Read LaTeX w/Errors
				write_log(log, errors) 														# Log - Log the Errors
			else:
				write_log(log, 'LaTeX PDF: Replaced LaTeX Content without Errors') 			# Log - Successfully Read LaTeX

			with open(latex_name, 'w') as f: 												# Create Tex File in Subject's Directory
				f.write(latex_content) 														# Write Content to Subject's LaTeX File
			write_log(log, 'LaTeX PDF: Created LaTeX File') 								# Log - Successfully Wrote New LaTeX


			## Control File
			bcf_name        = '{}/MRSinMRS.bcf'.format(self.cwd) 							# LaTeX Control File Template
			with open(bcf_name, 'r') as f: 													# Open LaTeX Control File Template
				bcf_content = f.read() 														# Read LaTeX Control File Template

			bcf_name    = '{}/{}.bcf'.format(LaTeX_dir, oname) 								# LaTeX Control File Filename
			bib_name    = '{}/{}.bib'.format(LaTeX_dir, oname) 								# LaTeX Bibliography Filename
			bcf_content = bcf_content.replace('/MRSinMRS.bib', bib_name) 					# Replace Generic Bilbiography Name
			with open(bcf_name, 'w') as f: 													# Create LaTeX Control File in Subject Directory
				f.write(bcf_content) 														# Write LaTeX Control File in Subject Directory
			write_log(log, 'LaTeX PDF: Created LaTeX Control file') 						# Log - Successfully Created PDF


			## LaTeX Extra Files
			shutil.copy('{}/MRSinMRS.aux'.format(self.cwd),  								# Generic LaTeX Auxilliary File
						'{}/{}.aux'.format(LaTeX_dir, oname)) 								# Subject LaTeX Auxilliary File

			shutil.copy('{}/MRSinMRS.bbl'.format(self.cwd),   								# Generic LaTeX Bibliography-formatted LaTeX
					    '{}/{}.bbl'.format(LaTeX_dir, oname)) 								# Subject LaTeX Bibliography-formatted LaTeX

			shutil.copy('{}/MRSinMRS.bib'.format(self.cwd),   								# Generic LaTeX Bibliography File
						'{}/{}.bib'.format(LaTeX_dir, oname)) 								# Subject LaTeX Bibliography File
			
			shutil.copy('{}/MRSinMRS.blg'.format(self.cwd),   								# Generic LaTeX Bibliography Log File
						'{}/{}.blg'.format(LaTeX_dir, oname)) 								# Subject LaTeX Bibliography Log File

			write_log(log, 'LaTeX PDF: Copied LaTeX Extra Files') 							# Log - Successfully Created PDF


			## Running PDFLaTeX
			if isinstance(shutil.which('pdflatex'), str) == True: 							# Check User has LaTeX Installed
				write_log(log, 'LaTeX PDF: PDFLaTeX is installed') 							# Log - Successfully Created PDF

				script = 'pdflatex -interaction=nonstopmode'
				script = '{} {}.tex > /dev/null 2>&1'.format(script, oname) 				# PDFLaTeX Script to call 
				P = subprocess.run(script, cwd=LaTeX_dir, shell=True) 						# Run PDFLaTeX Script
				write_log(log, 'LaTeX PDF: Created PDF from LaTeX') 						# Log - Successfully Created PDF

				shutil.move('{}/{}.tex'.format(LaTeX_dir, oname), pname) 					# Move LaTeX PDF to Subject Direcctory
				write_log(log, 'LaTeX PDF: Moved Tex to Subject Directory') 				# Log - Successfully Created PDF

				shutil.move('{}/{}.pdf'.format(LaTeX_dir, oname), pname) 					# Move LaTeX PDF to Subject Direcctory
				write_log(log, 'LaTeX PDF: Moved PDF to Subject Directory\n') 				# Log - Successfully Created PDF

			else: 																			# User does not have LaTeX installed
				write_log(log, 'LaTeX PDF: PDFLaTeX is not installed\n' + 					# Log - pdflatex not installed
							   'visit https://www.latex-project.org/get\n') 				# Log - pdflatex download page

		except Exception as e:
			write_log(log, 'LaTeX PDF: Failed Error Below') 								# Log - Failed to Populate Table
			write_log(log, 'LaTeX PDF: Error - {}\n'.format(e))  							# Log - Error


		write_log(log, 'Reproducibility Made Easy has Completed!') 							# Log - Failed to Populate Table
		write_log(log, '--'*30)  															# Log - Dashed Line to Separate Entries
		self.command_03['text'] = 'Completed!' 												# Note Completion

class Table():
	def __init__(self):
		
		if getattr(sys, 'frozen', False): 													# Determine if Executable or Command Line
			# print('Inside executable')
			# self.cwd = os.path.dirname(sys.executable) 										# Executable
			self.cwd = os.path.abspath(os.path.dirname(__file__))

		elif __file__: 																		#
			self.cwd = os.path.dirname(os.path.realpath(__file__)) 							# Command Line 


		self.cwd                   = self.cwd.replace('\\', '/')	 						# Replace any Windows' Backslash
		self.MRSinMRS_Table        = pd.read_csv('{}/MRSinMRS.csv'.format(self.cwd))
		self.latex_file            = '{}/MRSinMRS.tex'.format(self.cwd) 						# Generic LaTeX File

		# print('Read in MRSinMRS Table')

	def table_clean(self, vendor, datatype, MRSinMRS): 										# Differences Across Datatype Version
		vendor                 = vendor.lower()

		if vendor.lower() == "philips" and datatype.lower() == "sdat":
			datatype = "spar"

		vendor_string          = 's2nlabel_{}_{}'.format(vendor, datatype).lower() 			# Identify Vendor
		vendor_keys            = list(self.MRSinMRS_Table[vendor_string]) 					# Get Vendor-specific fields
		mrs_keys               = list(MRSinMRS.keys()) 										# Get MRSinMRS Dictionary Items

		known_diffs            = {} 														# Known Differences In Header Field Names
		known_diffs['siemens'] = {'FieldStrength'   : ['lFrequency'           ,				# Siemens Dictionary
													   'Frequency'            ,
													   'SpectrometerFrequency'], 			#
								  'NumberOfAverages': ['Averages',            ], 			# 
								  'DwellTime'       : ['DwellTimeSig',        ], 			# 
								  'tProtocolName'   : ['SequenceFileName',    ], 			# 
								  'Nucleus'         : ['ResonantNucleus',     ]} 			# 
		known_diffs['philips'] = {'FieldStrength'   : ['synthesizer_frequency'], 			# Philips Dictionary 
								  'EchoTime'        : ['echo_time',           ], 	 		#
							 	  'RepetitionTime'  : ['repetition_time',     ], 			# 
							 	  'Nucleus'         : ['nucleus'              ]} 			# 
		known_diffs['ge'     ] = {'FieldStrength'   : ['rhr_rh_ps_mps_freq'   ]} 			# GE
		known_diffs['bruker' ] = {} 														# Bruker

		known_diffs            = known_diffs[vendor] 	 									# Current Vendor	
		known_diffs_keys       = list(known_diffs.keys()) 									# List of all Known Differences

		for ii in range(len(known_diffs_keys)): 											# Iterate over Known Differences
			if (known_diffs_keys[ii] not in mrs_keys) == True: 								# If Key was not found in Data Reading 
				known_diffs_keys_list = known_diffs[known_diffs_keys[ii]] 					# Get the list of potential differences

				for jj in range(len(known_diffs_keys_list)): 								# Iterate over differences
					if (known_diffs_keys_list[jj] in mrs_keys) == True: 					# This Item was found in Data Reading
						MRSinMRS[known_diffs_keys[ii]]= MRSinMRS[known_diffs_keys_list[jj]] # Update with Item Found from Difference

		if 'Nucleus' in list(MRSinMRS.keys()):
			gyro       = {				 													# Gyromagnetic Ratio (MHz/Tesla) or (γ/2π)
						  '1H'  : 42.5760, 													#  1H  Proton
						  '2H'  :  6.5360, 													#  2H  Deuterium
					      '13C' : 10.7084, 													# 13C  Carbon
						  '15N' : -4.3160,													# 15N  Nitrogen
						  '17O' : -5.7720, 													# 17O  Oxygen
						  '23Na': 11.2620, 													# 23Na Sodium
						  '31P' : 17.2350}													# 31P  Phosphorous

			vendor_divs = {'siemens_dat'  : 1e6, 											# Siemens Twix
						   'siemens_ima'  : 1  , 											# Siemens Dicom
						   'philips_spar' : 1e6, 											# Philips Spar
						   'ge_7'         : 1e7, 											# GE Pfile
						   'bruker_method': 1  , 											# Bruker Method
						   'bruker_2dseq' : 1  ,} 											# Bruker 2dseq

			gyro        = gyro[MRSinMRS['Nucleus']] 										# Nucleus Gyromagnetic Ratio
			vendor_divs = vendor_divs['{}_{}'.format(vendor, datatype)] 					# Units

			MRSinMRS['FieldStrength'] = float(MRSinMRS['FieldStrength']) / gyro 			# Field Strenth in T
			MRSinMRS['FieldStrength'] =  MRSinMRS['FieldStrength'] / vendor_divs			# Field Strenth in T
			MRSinMRS['FieldStrength'] = np.round(MRSinMRS['FieldStrength'], 2) 				# Field Strenth rounded

		return MRSinMRS 																	# Return Clean MRSinMRS Dict

	def populate(self, vendor, datatype, MRSinMRS):  										# Populate our MRSinMRS Table

		if vendor.lower() == "philips" and datatype.lower() == "sdat":
			datatype = "spar"

		vendor_string   = 's2nlabel_{}_{}'.format(vendor, datatype).lower() 				# Identify Vendor

		vendor_keys     = list(self.MRSinMRS_Table[vendor_string]) 							# Get Vendor-specific fields
		mrs_keys        = list(MRSinMRS.keys()) 											# Get MRSinMRS Dictionary Items

		MRSinMRS_values = []   																# Store Values in List
		for ii in range(len(vendor_keys)):			 										# Iterate over Vendor Fields
			if isinstance(vendor_keys[ii], str) == True and vendor_keys[ii] in mrs_keys: 	# If Item in Vendor Fields
				MRSinMRS_values.append(MRSinMRS[vendor_keys[ii]]) 							# Add Item
			else: 	 																		# Not in Vendor Fields
				MRSinMRS_values.append('') 													# Skip Item

		self.MRSinMRS_Table['Values'] = MRSinMRS_values 									# Add Values to MRSinMRS Table

	def table_to_latex(self,): 																# Convert Table to LaTeX
		
		mrs_fields = list(self.MRSinMRS_Table.Generic) 										# Generic Field Names
		errors     = '' 																	# Instatiate String to Log Errors

		with open(self.latex_file, 'r') as f: 												# Open Generic LaTeX File
			latex_content = f.read() 														# Read Content
			latex_fields  = re.findall(r'\\textbf{(\w+)}', latex_content) 					# Find Fields to Replace

		for ii in range(len(latex_fields)): 												# Iterate over Fields

			try: 																			# Try to Catch Errors
				if latex_fields[ii] in mrs_fields: 											# If Field to Replace is in Table
					df       = copy.deepcopy(self.MRSinMRS_Table) 							# Copy Table
					df       = df[df.Generic == latex_fields[ii]].reset_index(drop=True) 	# Get Copied Table Row
					df_value = str(df.Values[0]) 											# Get Field's Value as String
					df_value = df_value.replace('_', '') 									# Remove any underscores for LaTeX

					if len(df_value) > 2: 													# Empty Strings - Should be > 2 characters
						latex_content = latex_content.replace('\\textbf{{{}}}'.format(      # Replace with Field's Value
																latex_fields[ii]), df_value)						
			
			except Exception as e: 															# Catch Errors
				errors = '{}\nLaTeX Fx : {:3d} {} {}'.format(errors, ii, latex_fields[ii], e)
				print('Error: ', e) 														# Note Error

		return latex_content, errors

class DataReaders():
	def siemens_twix(self, fname, log):

		## Siemens Twix
		write_log(log, 'Data Read: Siemens Twix') 											# Log - Twix
		try:
			from mapvbvd import mapVBVD  													# Siemens File Reading with pymapVBVD
			twixObj  = mapVBVD(fname, quiet=True)  														# Get Twix Object

			if isinstance(twixObj, list) == True:
				twixHd   = twixObj[1]['hdr'] 												# Get Twix Header Single Header
			else:
				twixHd   = twixObj['hdr'] 													# Get Twix Header Multiple Headers

		except Exception as e:
			write_log(log, 'Data Read: Siemens Twix - Data Reader Failed') 					# Log - Note Failure
			write_log(log, 'Data Read: Siemens Twix - Error - {}'.format(e)) 				# Log - Note Error Message
			return {}, log 																	# Return Empty Dict and Log File


		## Successfully Read Data - Get Header Information
		write_log(log, 'Data Read: Siemens Twix - Data Reader Successful') 					# Log - Note Success
		MRSinMRS = {} 																		# Create MRSinMRS Dictionary to Populate
		MRSinMRS['Manufacturer'      ]  = 'Siemens'


		## Siemens Twix Object Fields
		dicom_header                    = list(twixHd['Dicom' ].keys())   					# Twix Object Dicom Header
		for ii in range(len(dicom_header)):	 												# Twix Object Dicom Header
			MRSinMRS[dicom_header[ii]]  = twixHd['Dicom' ][dicom_header[ii]]				# Twix Object Dicom Header

		config_header                   = list(twixHd['Config' ].keys())  					# Twix Object Config Header
		for ii in range(len(config_header)):	 											# Twix Object Config Header
			MRSinMRS[config_header[ii]] = twixHd['Config' ][config_header[ii]]				# Twix Object Config Header


		## Calculate Spectral Width - 
		#    Siemens doesn't automatically calculate 
		#    and DwellTime may be named differently across versions.
		headers                         = [] 												# Combine all the Headers
		headers.extend(dicom_header) 														# Dicom Header Fields
		headers.extend(config_header)														# Config Header Fields
		for ii in range(len(headers)): 														# Iterate over Header Fields
			if 'dwelltime' in headers[ii].lower(): 											# Find Dwell Time
				MRSinMRS['SpectralWidth'] =  1 / (float(MRSinMRS[headers[ii]]) * 1e-9) 		# Calulcate Spectral Width


		## Correct Echo/Repetition Time Units
		if 'TE' in list(MRSinMRS.keys()):
			if isinstance(MRSinMRS['TE'], str):
				MRSinMRS['TE'] = float(MRSinMRS['TE'].split(' ')[0]) / 1e6
			else: MRSinMRS['TE'              ]  = float(MRSinMRS['TE'   ]) / 1e6					# Echo Time
		if 'TR' in list(MRSinMRS.keys()):
			if isinstance(MRSinMRS['TR'], str):
				MRSinMRS['TR'] = float(MRSinMRS['TR'].split(' ')[0]) / 1e6
			MRSinMRS['TR'              ]  = float(MRSinMRS['TR'   ]) / 1e6  				# Repetition Time

		write_log(log, 'Data Read: Siemens Twix - Returning MRSinMRS Dictionary') 			# Log - Note Success
		return MRSinMRS, log 																# Return MRSinMRS Dictionary

	def siemens_ima(self, fname, log):

		## Siemens Dicom
		write_log(log, 'Data Read: Siemens Dicom') 											# Log - Siemens Dicom
		try:
			from spec2nii.Siemens.dicomfunctions import multi_file_dicom					# Read Siemens Dicom with spec2nii
			imageOut, _  = multi_file_dicom([fname], os.path.dirname(fname), None, False)  	# Get Siemens Dicom Object
			hdr          = imageOut[0].__dict__['_hdr_ext'].__dict__ 						# Siemens Dicom Header
			image        = imageOut[0].__dict__['image'   ].__dict__ 						# Siemens Dicom Image Params

		except Exception as e:
			write_log(log, 'Data Read: Siemens Dicom - Data Reader Failed') 				# Log - Note Failure
			write_log(log, 'Data Read: Siemens Dicom - Error - {}'.format(e)) 				# Log - Note Error Message
			return {}, log 																	# Return Empty Dict and Log File


		## Successfully Read Data - Get Header Information
		write_log(log, 'Data Read: Siemens Dicom - Data Reader Successful') 				# Log - Note Success
		MRSinMRS = {} 																		# Create MRSinMRS Dictionary to Populate
		MRSinMRS['Manufacturer'   ] = 'Siemens'
		MRSinMRS['Model'          ] = hdr['_standard_data'  ]['ManufacturersModelName'] 	# Siemens Model
		MRSinMRS['SoftwareVersion'] = hdr['_standard_data'  ]['SoftwareVersions'      ] 	# Siemens Version
		MRSinMRS['Nucleus'        ] = hdr['ResonantNucleus' ][0                       ] 	# Nucleus
		MRSinMRS['Sequence'       ] = hdr['_standard_data'  ]['ProtocolName'          ] 	# Sequence
		MRSinMRS['ap_size'        ] = image['_Nifti__pixdim'][0                       ] 	# Anterior Posterior
		MRSinMRS['lr_size'        ] = image['_Nifti__pixdim'][1                       ] 	# Left Right
		MRSinMRS['cc_size'        ] = image['_Nifti__pixdim'][2                       ] 	# CranioCaudal
		MRSinMRS['TR'             ] = hdr['_standard_data'  ]['RepetitionTime'        ] 	# TR
		MRSinMRS['TE'             ] = hdr['_standard_data'  ]['EchoTime'              ] 	# TE
		# MRSinMRS['TI'             ] = hdr['_standard_data'  ]['InversionTime'         ] 	# TI
		MRSinMRS['VectorSize'     ] = image['_Nifti__shape' ][3                       ] 	# Vector Size

		MRSinMRS['FieldStrength'  ] = hdr['SpectrometerFrequency'][0                  ] 	# Field Strength

		write_log(log, 'Data Read: Siemens Dicom - Returning MRSinMRS Dictionary') 			# Log - Note Success
		return MRSinMRS, log 																# Return MRSinMRS Dictionary


	def philips_spar(self, fname, log):

		## Philips SPAR
		write_log(log, 'Data Read: Philips SPAR ') 											# Log - 

		try:
			from spec2nii.Philips.philips import read_spar   								# Read Philips with spec2nii
			spar_params  = read_spar(fname) 												# Read spar (Header file)
			spar_params_ = list(spar_params.keys()) 										# Header Items

		except Exception as e:
			write_log(log, 'Data Read: Philips SPAR - Data Reader Failed') 					# Log - 
			write_log(log, 'Data Read: Philips SPAR - Error - {}'.format(e)) 				# Log - 
			return {}, log 																	# Return Empty Dict and Log File


		## Successfully Read Data - Get Header Information
		write_log(log, 'Data Read: Philips SPAR - Data Reader Successful') 					# Log Note Success
		MRSinMRS     = {} 																	# MRSinMRS Dictionary to Populate
		MRSinMRS['Manufacturer'] = 'Philips' 												# Manufacturer

		for ii in range(len(spar_params_)): 												# Iterate over Header items
			try:
				MRSinMRS[spar_params_[ii]] = spar_params[spar_params_[ii]] 					# Populate MRSinMRS Dictionary
				# print('{:3d}| {:<25} =  {}'.format(ii, spar_params_[ii], spar_params[spar_params_[ii]]))
			except Exception as e:
				print('{:3d}| {:<25} =  *** warning ***'.format(ii, spar_params_[ii], ))

		write_log(log, 'Data Read: Philips SPAR - Returning MRSinMRS Dictionary') 			# Log - Note Success
		return MRSinMRS, log 																# Return MRSinMRS Dictionary

	def ge_7(self, fname, log):

		write_log(log, 'Data Read: GE Pfile ') 												# Log - 

		try:
			from spec2nii.GE import ge_read_pfile 											# Read GE with spec2nii
			pfile    = ge_read_pfile.Pfile(fname) 											# Read Pfile
			dumped   = pfile._dump_struct(pfile.hdr) 										# Pfile Header

		except Exception as e:
			write_log(log, 'Data Read: GE Pfile - Data Reader Failed') 						# Log - 
			write_log(log, 'Data Read: GE Pfile - Error - {}'.format(e)) 					# Log - 
			return {}, log 																	# Return Empty Dict and Log File


		## Successfully Read Data - Get Header Information
		write_log(log, 'Data Read: GE Pfile - Data Reader Successful') 						# Log - 
		MRSinMRS = {} 																		# MRSinMRS Dictionary to Populate
		MRSinMRS['Manufacturer'      ] = 'GE' 												# Manufacturer

		cnt      = 0  																		# Iterator
		for info in dumped:             													# Iterate over Header Items
			if (info.label.find("pad") == 0): 												# Skip
				continue

			MRSinMRS[info.label] = info.value 												# Get Header Item
			cnt +=1 																		# Count

		MRSinMRS['rhi_tr'            ] = MRSinMRS['rhi_tr'            ] / 1e6 				# Repetition Time in Seconds
		MRSinMRS['rhi_te'            ] = MRSinMRS['rhi_te'            ] / 1e3 				# Echo Time in Milliseconds

		write_log(log, 'Data Read: GE Pfile - Returning MRSinMRS Dictionary') 				# Log - Note Success
		return MRSinMRS, log																# Return MRSinMRS Dictionary

	def bruker_2dseq(self, fname, log):

		write_log(log, 'Data Read: Bruker 2dseq') 											# Log - Note Success

		try:
			from brukerapi.dataset import Dataset  											# BrukerAPI from Tomáš Pšorn
			dataset  = Dataset(fname) 														# Read Bruker 2dseq File
		
		except Exception as e:
			write_log(log, 'Data Read: Bruker 2dseq - Data Reader Failed') 					# Log - 
			write_log(log, 'Data Read: Bruker 2dseq - Error - {}'.format(e)) 				# Log - 
			return {}, log 																	# Return Empty Dict and Log File

		## Successfully Read Data - Get Header Information
		write_log(log, 'Data Read: Bruker 2dseq - Successful') 								# Log - Note Success
		
		MRSinMRS = {} 																		# Create MRSinMRS Dictionary to Populate
		MRSinMRS['Manufacturer'   ] = 'Bruker' 												# Manufacturer is Bruker	
		MRSinMRS['FieldStrength'  ] = dataset.imaging_frequency								# Field Strength - Round to 1 decimal
		MRSinMRS['TR'          	  ] = dataset.TR 											# Repetition Time
		MRSinMRS['TE'          	  ] = dataset.TE 											# Echo Time
		MRSinMRS['Sequence'       ] = dataset.type 											# Echo Time
		MRSinMRS['Averages'       ] = dataset.shape_frames									# Number of Transients
		
		MRSinMRS['SoftwareVersion'] = 'PV {}'.format(dataset.pv_version)					# ParaVision Software Version

		write_log(log, 'Data Read: Bruker 2dseq - Returning MRSinMRS Dictionary') 			# Log - Note Success
		return MRSinMRS, log

	def bruker_method(self, fname, log):

		MRSinMRS = {} 																		# Create MRSinMRS Dictionary to Populate
		MRSinMRS['Manufacturer'   ] = 'Bruker' 												# Manufacturer is Bruker	


		## Read and Parse Method file
		with open(fname, 'r') as f: 														# Open
			method = f.read()		 														# Read
			method = method.split('##') 													# Split by Field


		## Convert Method file to MRSinMRS Dictionary
		for ii in range(len(method)): 														# Iterate
			if len(method[ii]) > 1: 														# If the line is not blank
				method[ii]    = method[ii].replace('\n', '; ') 								# Shorten Everything to 1 line
				method[ii]    = method[ii].split('=') 										# Split by Key and Value

				MRSinMRS[method[ii][0]] = method[ii][1] 									# Populate MRSinMRS Dictionary

		field_strength = MRSinMRS['$PVM_FrqRef'].split('; ')[1].split(' ')[0] 				# Bruker Field Strength
		field_strength = float(field_strength) 												# Bruker Field Strength in T

		TR             = float(MRSinMRS['$PVM_RepetitionTime'].replace(';', '')) 			# Repetition Time
		TE             = float(MRSinMRS['$PVM_EchoTime'].replace(';', '')) 					# Echo Time

		MRSinMRS = {} 																		# Create MRSinMRS Dictionary to Populate
		MRSinMRS['Manufacturer' ] = 'Bruker' 												# Manufacturer		
		MRSinMRS['FieldStrength'] = field_strength											# Field Strength - Round to 1 decimal
		MRSinMRS['TR'          	] = TR														# Repetition Time
		MRSinMRS['TE'          	] = TE 														# Echo Time
		
		return MRSinMRS, log


if __name__ == '__main__':
	app = Application(lwrite=True)
	app.mainloop()

