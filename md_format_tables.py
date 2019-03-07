#!/usr/bin/python

def md_convert_tables(md_input):
	
	#iterate over lines
	lines = md_input.split('\n')
	md_output = ''

	i=0

	while (i<len(lines)):
		
		#tables start with |
		if (lines[i][:1]=='|'):

			# append all lines belonging to the same table row
			while(i<len(lines) and lines[i][-1:]!='|'):
				md_output += lines[i] + ' '
				i+=1
			#last line ends with |
			md_output += lines[i]

		#otherwise this is not a table
		else:
			md_output += lines[i]
		
		md_output += '\n'
		i+=1

	return md_output


def md_files_convert():
	input_file  = open('table.txt')
	output_file = open('table2.txt','w')
	output_file.write(md_convert_tables(input_file.read()))


md_files_convert()