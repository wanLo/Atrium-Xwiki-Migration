#!/usr/bin/python

# files to be replaced with REST-Requests
file1 = open('table.txt')
md_input = file1.read()
file2 = open('table2.txt','w')

#iterate over lines
lines = md_input.split('\n')
md_output = ''

i=0

while (i<len(lines)):
	
	#append all following lines of a table row
	if (lines[i][:1]=='|'):
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

file2.write(md_output)