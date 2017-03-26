import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint

#OSM file to audit, this file uses the elgin_sample which is a small sample of the full xml used for the project
OSMFILE = "elgin_sample.osm"
#OSMFILE = "map.osm"

#Regular expressions to aid with examining/reformatting data
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
state_type_re = re.compile(r'[A-Za-z+]+')
phone_number_re = re.compile(r'^(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$')
post_code_re = re.compile(r'\d{5}')
city_type_re = re.compile(r'^([\w\-]+)')
housenumber_re = re.compile(r'\d+')

#List of street types that do not require reformatting
expected = ["Wren", "West", "Way", "Walk", "Trace", "Talamore", "Ridge", "Reinhardt", "Ravine", "Pointe", "Pine", "Path", "Pass", 
            "Park", "North", "Maple", "Loop", "Landing", "Juniper", "East", "Crossing", "Cove", "Cliff", "CastlePath", "Castle", 
            "Canterwood", "Bend", "Drive", "Boulevard", "973", "685", "619", "459", "3177", "290", "275", "138", "129", "1100",
            "Court", "Lane", "Square", "Avenue", "Trail", "Street", "Place", "Terrace", "Parkway", "Circle", "Road"]

#Dictionary of street types that I decided to reformat
mapping = { "St": "Street",
            "St.": "Street",
            "Ave": "Avenue",
            "Blvd": "Boulevard",
            "Rd.": "Road",
            "Rd": "Road",
            "street": "Street",
            "Trl": "Trail",
            "Ln": "Lane",            
            "Dr": "Drive",
            "Cv": "Cove",
            "Ct": "Court",
            "Cc": "Cove",
            "pass": "Pass",
            "Terrance": "Terrace"
            }


def audit(osmfile):
    osm_file = open(osmfile, "r")

#Create a data structure for each value field.
    street_types = defaultdict(set)
    state_types = defaultdict(set)
    post_code_types = []
    city_types = defaultdict(set)
    housenumber_types = defaultdict(set)    
    phone_number_types = []

#Check each iterated tag for the appropriate value, and call the audit function to add to the data structure
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])
                elif is_state(tag):
                    audit_state_type(state_types, tag.attrib['v'])
                elif is_phone_number(tag):
                    audit_phone_number(phone_number_types, tag.attrib['v'], )
                elif is_post_code(tag):
                    audit_post_code_type(post_code_types, tag.attrib['v'])
                elif is_city(tag):
                    audit_city_type(city_types, tag.attrib['v'])
                elif is_housenumber(tag):
                    audit_housenumber_type(housenumber_types, tag.attrib['v'])
                else:
                    continue

    osm_file.close()

    return street_types, state_types, phone_number_types, post_code_types, city_types, housenumber_types

#These functions check which value the input field is, and add the value to a data structure
def is_phone_number(elem):
    return (elem.attrib['k'] == "phone")

def audit_phone_number(phone_number_types, phone_number):
    phone_number_types.append(phone_number)

def is_post_code(elem):
    return (elem.attrib['k'] == "addr:postcode")

def audit_post_code_type(post_code_types, post_code):
    post_code_types.append(post_code)
    
def is_city(elem):
    return (elem.attrib['k'] == "addr:city")

def audit_city_type(city_types, city_name):
    audit_city = city_type_re.search(city_name)
    if audit_city:
        city_type = audit_city.group()
        city_types[city_type].add(city_name)

def is_housenumber(elem):
    return (elem.attrib['k'] == "addr:housenumber")

def audit_housenumber_type(housenumber_types, housenumber):
    audit_housenumber = housenumber_re.search(housenumber)
    if audit_housenumber:
        housenumber_type = audit_housenumber.group()
        housenumber_types[housenumber_type].add(housenumber) 

def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")

def audit_street_type(street_types, street_name):
    audit_street = street_type_re.search(street_name)
    if audit_street:
        street_type = audit_street.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)

def is_state(elem):
    return (elem.attrib['k'] == 'addr:state')

def audit_state_type(state_types, state_name):
    audit_state = state_type_re.search(state_name)
    if audit_state:
        state_type = audit_state.group()
        state_types[state_type].add(state_name)

def test():
    #audit function returns several data structures, the below statement assigns each to its own variable
    street_dict, state_dict, phone_number_dict, post_code_dict, city_dict, housenumber_dict = audit(OSMFILE)
    
    #Use the below print statements to look at each data structure, comment them in and out to only see one at a time
    #pprint.pprint(dict(state_dict))
    #pprint.pprint(dict(housenumber_dict))
    pprint.pprint(dict(city_dict))
    '''post_code_set = set(post_code_dict)
    pprint.pprint(post_code_set)'''
    #pprint.pprint(dict(street_dict))
    #pprint.pprint(phone_number_dict)

if __name__ == '__main__':
    test()