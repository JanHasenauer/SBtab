#!/usr/bin/env python
import re, libsbml
import SBtab
import tablibIO

#all allowed SBtab types (except for Compound and Reaction, which are somewhat mandatory)
sbtab_types = ['Quantity'] #['Enzyme','Compartment']

class ConversionError(Exception):
    def __init__(self,message):
        self.message = message
    def __str__(self):
        return self.message

class SBtabDocument:
    '''
    SBtab document to be converted to SBML model
    '''
    def __init__(self,sbtab_document,filename,tabs=1):
        '''
        initalize SBtab document, check it for SBtabs
        '''
        self.document = [sbtab_document]
        self.filename = filename
        self.tabs     = tabs

        if self.filename.endswith('tsv') or self.filename.endswith('csv') or self.filename.endswith('.xls'): pass
        else: raise ConversionError('The given file format is not supported: '+self.filename)

        (sbtabs,types) = self.checkTabs()              #check how many SBtabs are given in the document

    def checkTabs(self,doc=None):
        '''
        this function checks, how many SBtab files are given by the user and save it/them
        in a list, moreover store the SBtab types in a dict linking to the SBtabs
        '''
        self.sbtabs     = []
        #self.types      = []
        self.type2sbtab = {}

        #if there are more than one SBtabs given in single files that might be comprised of several SBtabs:
        if self.tabs > 1:
            #print '1'
            for single_document in self.document[0]:
                #check for several SBtabs in one document
                document_rows = single_document.split('\n')
                tabs_in_document = self.getAmountOfTables(document_rows)
                if tabs_in_document > 1:
                    sbtabs = self.splitDocumentInTables(document_rows)
                else: sbtabs = [document_rows]
                #generate SBtab class instance for every SBtab
                for sbtab in sbtabs:
                    sbtabtsv = self.unifySBtab(sbtab)
                    new_tablib_obj = tablibIO.importSetNew(sbtabtsv,self.filename)
                    single_tab = SBtab.SBtabTable(new_tablib_obj,self.filename)
                    self.type2sbtab[single_tab.table_type] = single_tab
        #elif there is only one document given, possibly consisting of several SBtabs
        else:
            #print '2'
            #check for several SBtabs in one document
            #print self.document[0][0]
            document_rows    = self.document[0][0].split('\n')
            tabs_in_document = self.getAmountOfTables(document_rows)
            if tabs_in_document > 1: sbtabs = self.splitDocumentInTables(document_rows)
            else: sbtabs = [document_rows]
            #generate SBtab class instance for every SBtab
            for sbtab in sbtabs:
                as_sbtab = '\n'.join(sbtab)
                new_tablib_obj = tablibIO.importSetNew(as_sbtab,self.filename)
                single_tab = SBtab.SBtabTable(new_tablib_obj,self.filename)
                self.type2sbtab[single_tab.table_type] = single_tab

        return sbtabs,self.type2sbtab

    def unifySBtab(self,sbtab):
        '''
        if we have a list of heterogeneous SBtab files, we have to unify them to one common delimiter; we choose \t arbitrarily
        '''
        new_tab = []

        for row in sbtab:
            if row.startswith('!!'): continue
            if row.startswith('!'):
                columns = row
                if '\t' in columns:
                    new_tab = sbtab
                    break
                elif ';' in columns:
                    delimiter = ';'
                    new_tab.append(sbtab[0].replace(delimiter,'\t'))
                    new_tab.append(sbtab[1].replace(delimiter,'\t'))
                    continue
                elif ',' in columns:
                    delimiter = ','
                    new_tab.append(sbtab[0].replace(delimiter,'\t'))
                    new_tab.append(sbtab[1].replace(delimiter,'\t'))
                    continue
                else:
                    print 'The delimiter of one of the SBtabs could not be identified. Please check.'
            new_tab.append(row.replace(delimiter,'\t'))

        new_tab = '\n'.join(new_tab)

        return new_tab
            
    def getAmountOfTables(self,document_rows):
        '''
        counts the SBtab tables that are present in the document
        '''
        counter = 0
        for row in document_rows:
            if row.startswith('!!'):
                counter += 1
        return counter

    def splitDocumentInTables(self,document_rows):
        '''
        if the document contains more than one SBtab, this function splits the document
        into the single SBtabs
        '''
        single_sbtab = [document_rows[0]]
        sbtab_list   = []
        for row in document_rows[1:]:
            if not row.startswith('!!'): single_sbtab.append(row)
            else:
                sbtab_list.append(single_sbtab)
                single_sbtab = [row]
        sbtab_list.append(single_sbtab)
        return sbtab_list

    def makeSBML(self):
        '''
        generates the SBML file using the mandatory reaction SBtab file
        '''
        # initialize new model
        self.new_document = libsbml.SBMLDocument()
        self.new_model    = self.new_document.createModel()
        self.new_model.setId('default_id')
        self.new_model.setName('default_name')
        self.new_document.setLevelAndVersion(2,4)
        self.reaction_list    = []
        self.species_list     = []
        self.compartment_list = []
        self.modifier_list    = []
        self.id2sbmlid        = {}

        #0st order: create compartments
        
        self.compartmentSBtab()
        '''
        except:
            default_compartment = self.new_model.createCompartment()
            default_compartment.setId('Default_Compartment')
            default_compartment.setName('Default_Compartment')
            default_compartment.setSize(1)
            self.compartment_list.append('Default_Compartment')
            #self.new_model.addCompartment(default_compartment)
            #for species in self.new_model.getListOfSpecies():
            #    if not species.isSetCompartment():
            #        species.setCompartment('Default_Compartment')   
        '''
        

        #1st order of bizness: due to the right modeling order of SBML, we first check for a compound SBtab
        if 'Compound' in self.type2sbtab.keys():
            self.compoundSBtab()

        #2nd order of bizness: Work the Reaction SBtab (mandatory)
        self.reactionSBtab()

        #3rd order: check, which other SBtabs are given
        for sbtab in sbtab_types:
            try:
                self.type2sbtab[sbtab]
                name = 'self.'+sbtab.lower()+'SBtab()'
                eval(name)
            except:
                pass

        #Last, but not least: generate the SBML model
        #libsbml.writeSBML(self.new_document,'New_Model.xml')
        newSBML = libsbml.writeSBMLToString(self.new_document)#newSBML

        return newSBML

    def enzymeSBtab(self):
        '''
        extract the information from the Enzyme SBtab and write it to the model
        '''
        sbtab = self.type2sbtab['Enzyme']

        for row in sbtab.value_rows:
            if row[sbtab.columns_dict['!Enzyme']] not in self.species_list:
                species = self.new_model.createSpecies()
                species.setId(str(row[sbtab.columns_dict['!Enzyme']]))
                if '!Name' in sbtab.columns and not row[sbtab.columns_dict['!Name']] == '':
                    if '|' in row[sbtab.columns_dict['!Name']]: species.setName(str(row[sbtab.columns_dict['!Name']].split('|')[0]))
                    else: species.setName(str(row[sbtab.columns_dict['!Name']]))
                #self.new_model.addSpecies(species)                
            if row[sbtab.columns_dict['!Enzyme']] not in self.modifier_list:
                for reaction in self.new_model.getListOfReactions():
                    if reaction.getId() == row[sbtab.columns_dict['!Reaction']]:
                        modifier = reaction.createModifier()
                        modifier.setSpecies(row[sbtab.columns_dict['!Enzyme']])


    def compartmentSBtab(self):
        '''
        extract the information from the Compartment SBtab and write it to the model
        '''
        sbtab     = self.type2sbtab['Compartment']
        comp2size = {}
        
        #complement the missing compartments
        for row in sbtab.value_rows:
            if row[sbtab.columns_dict['!Compartment']] not in self.compartment_list:
                compartment = self.new_model.createCompartment()
                if '!SBMLCompartmentID' in sbtab.columns and row[sbtab.columns_dict['!SBMLCompartmentID']] != '': compartment.setId(str(row[sbtab.columns_dict['!SBMLCompartmentID']]))
                else: compartment.setId(str(row[sbtab.columns_dict['!Compartment']]))
                if '!Name' in sbtab.columns and not row[sbtab.columns_dict['!Name']] == '':
                    if '|' in row[sbtab.columns_dict['!Name']]: compartment.setName(str(row[sbtab.columns_dict['!Name']].split('|')[0]))
                    else: compartment.setName(str(row[sbtab.columns_dict['!Name']]))
            self.compartment_list.append(row[sbtab.columns_dict['!Compartment']])
                #self.new_model.addCompartment(compartment)

            #set the compartment sizes if given
            if '!Size' in sbtab.columns:
                for comp in self.new_model.getListOfCompartments():
                    for compsbtab in sbtab.value_rows:
                        if comp.getId() == compsbtab[sbtab.columns_dict['!Compartment']] and compsbtab[sbtab.columns_dict['!Size']] != '':
                            comp.setSize(float(compsbtab[sbtab.columns_dict['!Size']]))

    def compoundSBtab(self):
        '''
        extract the information from the Compound SBtab and write it to the model
        '''
        sbtab = self.type2sbtab['Compound']

        for row in sbtab.value_rows:
            if not row[sbtab.columns_dict['!Compound']] in self.species_list:
                species = self.new_model.createSpecies()
                if '!SBMLSpeciesID' in sbtab.columns and row[sbtab.columns_dict['!SBMLSpeciesID']] != '':
                    species.setId(str(row[sbtab.columns_dict['!SBMLSpeciesID']]))
                    self.id2sbmlid[row[sbtab.columns_dict['!Compound']]] = row[sbtab.columns_dict['!SBMLSpeciesID']]
                else:
                    species.setId(str(row[sbtab.columns_dict['!Compound']]))
                    self.id2sbmlid[row[sbtab.columns_dict['!Compound']]] = None
                if '!Name' in sbtab.columns and not row[sbtab.columns_dict['!Name']] == '':
                    if '|' in row[sbtab.columns_dict['!Name']]: species.setName(str(row[sbtab.columns_dict['!Name']].split('|')[0]))
                    else: species.setName(str(row[sbtab.columns_dict['!Name']]))
                self.species_list.append(species)
                #check out the speciestype if possible
                if '!SpeciesType' in sbtab.columns and row[sbtab.columns_dict['!SpeciesType']] != '':
                    species_type = self.new_model.createSpeciesType()
                    species_type.setId(str(row[sbtab.columns_dict['!SpeciesType']]))
                    species.setSpeciesType(row[sbtab.columns_dict['!SpeciesType']])
                #if compartments are given, add them
                if '!Location' in sbtab.columns and row[sbtab.columns_dict['!Location']] != '':
                    if not row[sbtab.columns_dict['!Location']] in self.compartment_list:
                        new_comp = self.new_model.createCompartment()
                        new_comp.setId(str(row[sbtab.columns_dict['!Location']]))
                        self.compartment_list.append(row[sbtab.columns_dict['!Location']])
                    species.setCompartment(row[sbtab.columns_dict['!Location']])
                if '!InitialConcentration' in sbtab.columns and row[sbtab.columns_dict['!InitialConcentration']] != '':
                    species.setInitialConcentration(float(row[sbtab.columns_dict['!InitialConcentration']]))
                #DEPRECATED: Libsbml does not want this anymore!
                #is the charge at hand? if so: set
                #if sbtab.charge_column and row[sbtab.charge_column] != '':
                #    species.setCharge(int(row[sbtab.charge_column]))
                #is the species a constant and we have this information?
                if '!Constant' in sbtab.columns and row[sbtab.columns_dict['!Constant']] != '':
                    species.setConstant(row[sbtab.columns_dict['!Constant']].lower())

        #species without compartments yield errors --> set them to the first available compartment
        for species in self.new_model.getListOfSpecies():
            if not species.isSetCompartment():
                species.setCompartment(self.compartment_list[0])

    def reactionSBtab(self):
        '''
        extract the information from the Reaction SBtab and write it to the model
        '''
        sbtab = self.type2sbtab['Reaction']

        #if we have the sumformulas, extract the reactants and create the species
        if '!SumFormula' in sbtab.columns:
            self.getReactants(sbtab)
            for reaction in self.reaction2reactants:
                compartment = self.reaction2compartment[reaction]
                educts      = self.reaction2reactants[reaction][0]
                for educt in educts:
                    if not educt in self.id2sbmlid.keys() and not educt in self.species_list:
                        sp = self.new_model.createSpecies()
                        sp.setId(str(educt))
                        sp.setName(str(educt))
                        sp.setInitialConcentration(1)
                        sp.setCompartment(compartment)
                        self.species_list.append(educt)
                products = self.reaction2reactants[reaction][1]
                for product in products:
                    if not product in self.id2sbmlid.keys() and not product in self.species_list:
                        sp = self.new_model.createSpecies()
                        sp.setId(str(product))
                        sp.setName(str(product))
                        sp.setInitialConcentration(1)
                        sp.setCompartment(compartment)
                        self.species_list.append(product)

        #if compartments are given for the reactions and these compartments are not built yet:
        if '!Location' in sbtab.columns:
            for row in sbtab.value_rows:
                if row[sbtab.columns_dict['!Location']].startswith('No compartment'):
                    continue
                if row[sbtab.columns_dict['!Location']] not in self.compartment_list:
                    compartment = self.new_model.createCompartment()
                    compartment.setId(row[sbtab.columns_dict['!Location']])
                    compartment.setName(row[sbtab.columns_dict['!Location']])
                    compartment.setSize(1)
                    self.compartment_list.append(row[sbtab.columns_dict['!Location']])
                        
        #creating the reactions
        for row in sbtab.value_rows:
            #if the reaction must not be included in the model: continue
            try:
                sbtab.columns_dict['!BuildReaction']
                if row[sbtab.columns_dict['!BuildReaction']] == 'False':
                    continue
            except: pass

            react = self.new_model.createReaction()
            try:
                sbtab.columns_dict['!SBMLReactionID']
                if row[sbtab.columns_dict['!SBMLReactionID']] != '':
                    react.setId(str(row[sbtab.columns_dict['!SBMLReactionID']]))
            except: react.setId(str(row[sbtab.columns_dict['!Reaction']]))

            #get the reaction name
            try:
                sbtab.columns_dict['!Name']
                if not row[sbtab.columns_dict['!Name']] == '':
                    if '|' in row[sbtab.columns_dict['!Name']]: react.setName(str(row[sbtab.columns_dict['!Name']].split('|')[0]))
                    else: react.setName(str(row[sbtab.columns_dict['!Name']]))
            except: react.setName(str(row[sbtab.columns_dict['!Reaction']]))

            #if sumformula is at hand: generate reactants and products
            try:
                sbtab.columns_dict['!SumFormula']
                if row[sbtab.columns_dict['!SumFormula']] != '':
                    for educt in self.reaction2reactants[react.getId()][0]:
                        reactant = react.createReactant()
                        if educt in self.id2sbmlid.keys():
                            if self.id2sbmlid[educt] != None: reactant.setSpecies(self.id2sbmlid[educt])
                            else: reactant.setSpecies(educt)
                        else: reactant.setSpecies(educt)
                        reactant.setStoichiometry(self.rrps2stoichiometry[row[sbtab.columns_dict['!Reaction']],educt])
                    for product in self.reaction2reactants[react.getId()][1]:
                        reactant = react.createProduct()
                        if product in self.id2sbmlid.keys():
                            if self.id2sbmlid[product] != None: reactant.setSpecies(self.id2sbmlid[product])
                            else: reactant.setSpecies(product)
                        else: reactant.setSpecies(product)
                        reactant.setStoichiometry(self.rrps2stoichiometry[row[sbtab.columns_dict['!Reaction']],product])
            except: pass
            '''
            #Uncomment, if we start using SBML Level 3, Version 1, or higher
            #if location is at hand: link reaction to the compartment
            if sbtab.columns_dict['!Location'] and row[sbtab.columns_dict['!Location']] != '':
                if not row[sbtab.columns_dict['!Location']] in self.compartment_list:
                    new_comp = self.new_model.createCompartment()
                    new_comp.setId(row[sbtab.columns_dict['!Location']])
                    react.setCompartment(new_comp)
                    self.compartment_list.append(row[sbtab.columns_dict['!Location']])
                else:
                    react.setCompartment(row[loc_column])
            '''

            #if an enzyme is given, mark it as modifier to the reaction
            try:
                sbtab.columns_dict['!Enzyme']
                if row[sbtab.columns_dict['!Enzyme']] != '':
                    if '!BuildEnzyme' in sbtab.columns and row[sbtab.columns_dict['!BuildEnzyme']] != 'False':
                        mod = react.createModifier()
                        if '!Enyzme SBMLSpeciesID' in sbtab.columns and row[sbtab.columns_dict['!Enyzme SBMLSpeciesID']] != '':
                            mod.setSpecies(row[sbtab.columns_dict['!Enyzme SBMLSpeciesID']])
                        elif '!Enzyme SBMLParameterID' in sbtab.columns and row[sbtab.columns_dict['!Enzyme SBMLParameterID']] != '': mod.setSpecies(row[sbtab.columns_dict['!Enzyme SBMLParameterID']])
                        else: mod.setSpecies(row[sbtab.columns_dict['!Enzyme']])
                        #react.addModifier(mod)
                    self.modifier_list.append(row[sbtab.columns_dict['!Enzyme']])
            except: pass
                    
            #if metabolic regulators are given: extract them and create them
            try:
                sbtab.columns_dict['!MetabolicRegulators']
                if row[sbtab.columns_dict['!MetabolicRegulators']] != '':
                    acts,inhs = self.extractRegulators(row[sbtab.columns_dict['!MetabolicRegulators']])
                    for activator in acts:
                        if activator in self.species_list and activator not in self.modifier_list:
                            acti = react.createModifier()
                            acti.setSpecies(activator)
                            acti.setSBOTerm(459)
                            #react.addModifier(acti)
                            self.modifier_list.append(acti)
                    for inhibitor in inhs:
                        if inhibitor in self.species_list and inhibitor not in self.modifier_list:
                            inhi = react.createModifier()
                            inhi.setSpecies(inhibitor)
                            inhi.setSBOTerm(20)
                            #react.addModifier(inhi)
                            self.modifier_list.append(inhi)
            except: pass



    def extractRegulators(self,mods):
        '''
        extracts the regulators from the column "MetabolicRegulators"
        '''
        activators = []
        inhibitors = []

        splits = mods.split(' ')

        for i,element in enumerate(splits):
            if element == '+': activators.append(splits[i+1])
            elif element == '-': inhibitors.append(splits[i+1])

        return activators,inhibitors

        
    def getReactants(self,sbtab):
        '''
        extracts the reactants from the sum formula
        '''
        self.reaction2reactants   = {}
        self.rrps2stoichiometry   = {}
        self.reaction2compartment = {}
        educts   = []
        products = []
        
        for reaction in sbtab.value_rows:
            if '!Reaction' in sbtab.columns and reaction[sbtab.columns_dict['!Reaction']] != '': r_id = reaction[sbtab.columns_dict['!Reaction']]
            else: r_id   = reaction[sbtab.columns_dict['!Reaction']]
            if '!Location' in sbtab.columns: self.reaction2compartment[r_id] = reaction[sbtab.columns_dict['!Location']]
            sum_formula  = reaction[sbtab.columns_dict['!SumFormula']]
            #is a compartment given for the reaction? (nice, but we cannot set it (only in SBML version 3))
            if sum_formula.startswith('['): self.reaction2compartment[r_id] = re.search('[([^"]*)]',sum_formula).group(1)
            #check the educts
            educt_list   = re.search('([^"]*)<=>',sum_formula).group(1)
            educts       = []
            for educt in educt_list.split('+'):
                if educt.lstrip().rstrip().split(' ')[0].isdigit():
                    self.rrps2stoichiometry[r_id,educt.lstrip().rstrip().split(' ')[1]] = int(educt.lstrip().rstrip().split(' ')[0])
                    educts.append(educt.lstrip().rstrip().split(' ')[1])
                else:
                    self.rrps2stoichiometry[r_id,educt.lstrip().rstrip()] = 1
                    educts.append(educt.lstrip().rstrip())
            #check the products
            product_list = re.search('<=>([^"]*)',sum_formula).group(1)
            products     = []
            for product in product_list.split('+'):
                if product.lstrip().rstrip().split(' ')[0].isdigit():
                    self.rrps2stoichiometry[r_id,product.lstrip().rstrip().split(' ')[1]] = int(product.lstrip().rstrip().split(' ')[0])
                    products.append(product.lstrip().rstrip().split(' ')[1])
                else:
                    self.rrps2stoichiometry[r_id,product.lstrip().rstrip()] = 1
                    products.append(product.lstrip().rstrip())
                #products.append(product.lstrip().rstrip())
            self.reaction2reactants[r_id] = [educts,products]

    def quantitySBtab(self):
        '''
        '''
        sbtab = self.type2sbtab['Quantity']
        for row in sbtab.value_rows:
            #if row[sbtab.columns_dict['!Description']] == 'global parameter':
            parameter = self.new_model.createParameter()
            parameter.setId(row[sbtab.columns_dict['!SBML:parameter:id']])
            parameter.setUnits(row[sbtab.columns_dict['!Unit']])
            parameter.setValue(float(row[sbtab.columns_dict['!Value']]))
        
if __name__ == '__main__':
    sbtab_reaction = open('sbtabs/sbtab_reaction_full.tsv','r')
    sbtab_compound = open('sbtabs/sbtab_compound_full.tsv','r')
    #sbtab_enzyme = open('sbtabs/sbtab_enzyme_full.tsv','r')
    sbtab_quantity = open('sbtabs/sbtab_quantity_full.tsv','r')
    sbtab_compartment = open('sbtabs/sbtab_compartment_full.tsv','r')
    
    document = []
    document.append(sbtab_reaction.read())
    document.append(sbtab_compound.read())
    document.append(sbtab_quantity.read())
    document.append(sbtab_compartment.read())
    #document = [sbtab_reaction.read()+'\n\n'+sbtab_compound.read()]

    sbtab_reaction.close()
    sbtab_compound.close()
    sbtab_quantity.close()
    sbtab_compartment.close()

    sbtab_class = SBtabDocument(document,'bla.tsv',4)
    bla = sbtab_class.makeSBML()

    output = open('new_sbml.xml','w')
    output.write(bla)

    output.close()

    #sbtab_reaction.close()
    #sbtab_compound.close()
    #sbtab_quantity.close()
    #sbtab_compartment.close()
    