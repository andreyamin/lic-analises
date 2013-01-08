#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pylab import *
from mdlib import *	
import pandas

#xls = pandas.ExcelFile('/home/ewout/Dropbox/ATP/Administrativo/Redefor-2011-SEE.xls')
#see = xls.parse('USP_2011_FINAL',index_col = None)
#see['numero-cpf-int'] = see['numero-cpf'].apply(int)

# (ambiente,grade_item)
M2 = [(86,1832),(72,1455),(74,1499),(73,1478),(70,1363),(82,1695),(85,1808),(71,1392)]
M4 = [(91,2087),(81,1625),(77,1532),(88,1988),(89,1987),(75,1521),(90,1986),(76,1562)]

courses = {'Módulo 2':M2,
           'Módulo 4':M4}


def itemname(gradeitem):
    ''
    result = loaddata('select courseid, itemname from mdl_grade_items where id = %s' % gradeitem,moodle='moodle_lic2')
    if result.size:
        course = courseinfo(result[0,0])['shortname']
        iname = l2u(result[0,1])
        return course + ': ' + str(iname)


def notas(userids,gradeitem):
    ''

    def scalenota(gradeitem):
        result = loaddata('select scaleid from mdl_grade_items where id = %s' % gradeitem, moodle='moodle_lic2')
        if result:
            scaleid = result[0,0]
            result = loaddata('select scale from mdl_scale where id = %s' % scaleid,moodle='moodle_lic2')
            if result:
                scale = result[0,0].split(',')
                return lambda x: scale[x-1]

        
    def nota (userid,gradeitem): 
        result = loaddata('select finalgrade from mdl_grade_grades where itemid = %s and userid = %s' % (gradeitem,userid),from_cache=False,moodle='moodle_lic2')
        if result:
            return float(result[0,0])

    grades = [nota(userid,gradeitem) for userid in userids]
    grades = [round(nota,1) if nota else None for nota in grades]
    scale = scalenota(gradeitem)
    if scale:
        # Usar float(scale) assume que os strings da escala são 1 e 0
        # Isto só é válido para as presenças na escola!
        return [float(scale(int(nota))) if nota else None for nota in grades]
    else:
        return grades

def frame(course):
    ''
    first = True # hmm, não tem jeito melhor???
    for ambiente, gradeitem in course:
        #print gradeitem
        users = courseusers(ambiente)
        if users:
            userids = users['userid']
            gradename = itemname(gradeitem)
            grades = notas(userids,gradeitem)
            thisframe = pandas.DataFrame({'userid':userids})
            if first:
                frame = thisframe
                frame['Nome AVA'] = users['firstname']
                frame['Sobrenome AVA'] = users['lastname']
            
                frame['Número USP'] = users['idnumber']
                frame['Nome Júpiter'] = [pessoa(codpes)['nompes'] if codpes else '' for codpes in users['idnumber']]
                frame[gradename] = grades
                first = False
                continue
            thisframe[gradename] = grades
            # usamos um pandas.DataFrame para poder alinhar (join) as notas pelo userid facilmente        
            frame = pandas.merge(frame,thisframe, on = 'userid', how='outer')

#    # agora as colunas "atividade" dos ambientes
#    ambientes = [ambiente for (ambiente, gradeitem) in course]
#    #unique and sorted
#    ambientes = sorted(list(set(ambientes)))
#    for ambiente in ambientes:
#        users = courseusers(ambiente)
#        coursename = courseinfo(ambiente)['shortname']
#        if users:
#            userids = users['userid']
#            thisframe = pandas.DataFrame({'userid':userids})
#            thisframe['Atividade '+coursename] = [ativuser(userid,ambiente) for userid in userids]
#            frame = pandas.merge(frame,thisframe, on = 'userid', how='outer')
            

    # remover id do moodle antes de publicar
    del frame['userid'] 
    return frame

def moodle_date():
    return loaddata('select from_unixtime(timemodified) from mdl_grade_grades_history order by timemodified desc limit 1',from_cache=False,moodle='moodle_lic2')[0,0]

def query_yes_no(question, default="sim"):
    valid = {"sim":"sim",   "s":"sim",
             "não":"não",     "n":"não"}
    if default == None:
        prompt = " [s/n] "
    elif default == "sim":
        prompt = " [S/n] "
    elif default == "não":
        prompt = " [s/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Responda com  'sim' ou 'não' "\
                             "(ou 's' or 'n').\n")

def export_grades(courses,d='notas/', sync=False):
    ''
    import os, subprocess
    if not os.path.exists(d):
        makedir = query_yes_no("diretório "+d+" não existe. Criar?")
        if makedir == "sim":
            os.makedirs(d)
        else:
            return
    moodledate = moodle_date()
    dstr =  '-' + moodledate.strftime('%Y-%m-%d')
    for coursename,course in courses.iteritems():
        df = frame(course)
        outfile = os.path.join(d+'/',coursename+dstr)
        print "Writing to ", outfile
        df.to_csv(outfile + '.csv',index=False, sep='\t')
        try:
            # usar xlsx ao vez de xls aqui porque tem um problema com o xlwt e utf8...
            df.to_excel(outfile + '.xlsx', index = False)
        except ImportError:
            print "Faça um 'sudo pip install openpyxl' e tente novamente"            
    if sync:
        rstr = "rsync -av "+d+" atp.usp.br:/var/www/dados/lic/"
        print rstr
        subprocess.call(rstr,shell=True)

if __name__ == '__main__':
    import os
    d = os.path.expanduser('~/lic-analises/dados/notas')
    export_grades(courses,d, sync=False)
    print "Agora, faça um rsync -av "+d+" atp.usp.br:/var/www/dados/lic/"
    print "(Use rsync -av --delete se quiser remover arquivos inexistentes no diretório local do servidor remoto atp.usp.br)"
