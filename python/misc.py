"""
Miscellaneous SBtab functions
=============================
"""

#!/usr/bin/python
import re
import xlrd
import string

def first_row(sbtab_content,delimiter):
    '''
    Revokes a problem in the SBtab/tablib interface: tablib requires all rows to be
    equally long, but SBtab a differing length for the first row.

    Parameters
    ----------
    sbtab_content : str
       SBtab file as string.
    delimiter : str
       Delimiter of the column content; usually comma, tab, or semicolon.
    '''
    splitt =  sbtab_content.split('\n')
    new_content = ''
    for i,row in enumerate(splitt):
        splitrow = row.split(delimiter)
        if i == 0: new_content += splitrow[0]+'\n'
        else: new_content += delimiter.join(splitrow)+'\n'

    return new_content

def create_filename(sbtab_name, table_type, table_name):
    '''
    Creates a unique identifying name for an uploaded SBtab file to be displayed in the web interface.

    Parameters
    ----------
    sbtab_name : str
       SBtab file name as string.
    table_type : str
       SBtab attribute TableType
    table_name : str
       SBtab attribute TableName
    '''
    if table_name != '':
        if not table_type.lower() in sbtab_name[:-4].lower(): filename = sbtab_name[:-4]+'_'+table_type+'_'+table_name
        else: filename  = sbtab_name[:-4]+'_'+table_name
    else:
        if not table_type.lower() in sbtab_name[:-4].lower(): filename = sbtab_name[:-4]+'_'+table_type
        else: filename  = sbtab_name[:-4]

    return filename

def csv2xls(sbtab_file,delimiter):
    '''
    Converts SBtab file to xls file.

    Parameters
    ----------
    sbtab_file : str
       SBtab file as string.
    delimiter : str
       Delimiter of the column content; usually comma, tab, or semicolon.
    '''
    import xlwt
    import tempfile

    book  = xlwt.Workbook()
    sheet = book.add_sheet('Sheet 1')

    split_sbtab_file = sbtab_file.split('\n')

    first_row = sheet.row(0)
    first_row.write(0,split_sbtab_file[0])

    for i,row in enumerate(split_sbtab_file[1:]):
        new_row   = sheet.row(i+1)
        split_row = row.split(delimiter)
        for j,element in enumerate(split_row):
            new_row.write(j,element)

    #if something is stupid and it works
    #then it is not stupid:
    book.save('simple.xls')
    fileobject = open('simple.xls','r')

    return fileobject

def getDelimiter(sbtab_file_string):
    '''
    Determines the delimiter of an SBtab file.
    
    Parameters
    ----------
    sbtab_file_string : str
       SBtab file as string.
    '''
    
    try: rows = sbtab_file_string.split('\n')
    except: rows = sbtab_file_string
    sep = False
    
    for row in rows:
        if row.startswith('!!'): continue
        elif row.startswith('"!!'): continue
        if row.startswith('!'):
            s = re.search('(.)(!)',row)
            try: sep = s.group(1)
            except: pass

    if not sep:
        tabs_in_columnrow = rows[1].count('\t')
        commas_in_columnrow = rows[1].count(',')
        semicolons_in_columnrow = rows[1].count(';')
        if tabs_in_columnrow > commas_in_columnrow and tabs_in_columnrow > semicolons_in_columnrow: sep = '\t'
        elif commas_in_columnrow > tabs_in_columnrow and commas_in_columnrow > semicolons_in_columnrow: sep = ','
        elif semicolons_in_columnrow > tabs_in_columnrow and semicolons_in_columnrow > tabs_in_columnrow: sep = ';'

    #if delimiter was not found, count all delimiters in document and decide for the most frequent one
    if not sep:
        tabs       = sbtab_file_string.count('\t')
        commas     = sbtab_file_string.count(',')
        semicolons = sbtab_file_string.count(';')
        if tabs > commas and tabs > semicolons: sep = '\t'
        elif commas > tabs and commas > semicolons: sep = ','
        elif semicolons > tabs and semicolons > tabs: sep = ';'

    if not sep:
        sep = '\t'

    return sep

def removeDoubleQuotes(sbtab_file_string):
    '''
    Removes quotes and double quotes introduced by MS Excel

    Parameters
    ----------
    sbtab_file_string : str
       SBtab file as string.
    '''
    try: rows = sbtab_file_string.split('\n')
    except: rows = sbtab_file_string

    sbtab = []
    for row in rows:
        n1 = row.replace('""','#')
        if n1.startswith('!!'): n2 = n1
        else: n2 = n1.replace('"','')
        new_row = n2.replace('#','"')
        sbtab.append(new_row)

    new_sbtab = '\n'.join(sbtab)

    return new_sbtab
            
def xls2csv(xls_file,filename):
    '''
    Converts xls file to tsv file.
    
    Parameters
    ----------
    xls_file : xlrd object
       Excel sheet file as xlrd object.
    filename : str
       File name of the Excel file.
    '''
    workbook = xlrd.open_workbook(filename,file_contents=xls_file)
    sheet    = workbook.sheet_by_name(workbook.sheet_names()[0])

    getridof = []
    csv_file = []

    for i in range(sheet.nrows):
        stringrow = str(sheet.row(i))
        notext    = string.replace(stringrow,'text:u','')
        nonumbers = string.replace(notext,'number:','')
        noopenbra = string.replace(nonumbers,'[','')
        noclosebr = string.replace(noopenbra,']','')
        if '\"!!' in noclosebr:
            noone = string.replace(noclosebr,'\"',"")
            noapostr = string.replace(noone,"\'",'\"')
        else:
            noone    = string.replace(noclosebr,"\'",'')
            noapostr = string.replace(noone,'\u201d','\"')
        nocommas  = noapostr.split(', ')
        getridof.append(nocommas)

    for row in getridof:
        new_row = ''
        for elem in row:
            if not elem == "empty:''" and not elem == 'empty:' and not elem == 'empty:""': new_row += elem+','
            else: new_row += ','
        csv_file.append(new_row.rstrip(','))

    csv_file ='\n'.join(csv_file)

    return csv_file
        
