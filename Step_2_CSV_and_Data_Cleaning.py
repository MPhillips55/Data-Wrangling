import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET

import cerberus

import schema

OSM_PATH = "elgin_sample.osm"
#OSM_PATH = "map.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

#Regular expressions used to aid data cleaning section
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
state_type_re = re.compile(r'[A-Za-z+]+')
post_code_re = re.compile(r'\d{5}')
city_type_re = re.compile(r'^([\w\-]+)')

#These are the street types that did not require cleaning
expected = ["Wren", "West", "Way", "Walk", "Trace", "Talamore", "Ridge", "Reinhardt", "Ravine", "Pointe", "Pine", "Path", "Pass", 
            "Park", "North", "Maple", "Loop", "Landing", "Juniper", "East", "Crossing", "Cove", "Cliff", "CastlePath", "Castle", 
            "Canterwood", "Bend", "Drive", "Boulevard", "973", "685", "619", "459", "3177", "290", "275", "138", "129", "1100",
            "Court", "Lane", "Square", "Avenue", "Trail", "Street", "Place", "Terrace", "Parkway", "Circle", "Road"]

#Dictionary that contains the mapping information for street types that did require cleaning
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

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements
    
    if element.tag == 'node':
        #Records the top level attributes found in the NODE_FIELDS list, ignoring any others
        for node_field in NODE_FIELDS:
            node_attribs[node_field] = element.attrib[node_field]

        for child in element:            
            #dictionary to hold node tag information
            tag = {}
            if PROBLEMCHARS.search(child.attrib["k"]):
                continue
            elif LOWER_COLON.search(child.attrib['k']):
                process_child_tag_colon(element, child, default_tag_type, tag)

            #if there is no colon in the tag, the attributes are input as they are to the dict using the function call below    
            else:
                process_regular_child_tag(element, child, default_tag_type, tag)
            
            #the below statements perform the actual cleaning/standardization of the data using functions found in 'Helper Functions'
            if tag['key'] == 'street':
                street_name = tag['value']
                corrected_street_name = update_street_name(street_name, mapping)
                tag['value'] = corrected_street_name

            if tag['key'] == 'phone':
                phone_number = tag['value']
                corrected_phone_number = update_phone_number(phone_number)
                tag['value'] = corrected_phone_number
                    
            if tag['key'] == 'postcode':
                post_code = tag['value']
                corrected_post_code = update_post_code(post_code)
                tag['value'] = corrected_post_code
                    
            if tag['key'] == 'state':
                state_value = tag['value']
                corrected_state_value = update_state_name(state_value)
                tag['value'] = corrected_state_value
                    
            if tag['key'] == 'city':
                city_value = tag['value']
                corrected_city_value = update_city_name(city_value)
                tag['value'] = corrected_city_value
                        
            if tag:
                tags.append(tag)
        
        return {'node': node_attribs, 'node_tags': tags}
        
    elif element.tag == 'way':
        
        #processes ways similarly to nodes, with exception commented below
        for way_field in WAY_FIELDS:
            way_attribs[way_field] = element.attrib[way_field]
        
        for child in element:
            
            tag = {}
            way_node = {}

            if child.tag == 'tag':

                if PROBLEMCHARS.search(child.attrib['k']):
                    continue
                
                elif LOWER_COLON.search(child.attrib['k']):
                    process_child_tag_colon(element, child, default_tag_type, tag)

                else:
                    process_regular_child_tag(element, child, default_tag_type, tag)

                if tag['key'] == 'street':
                    street_name = tag['value']
                    corrected_street_name = update_street_name(street_name, mapping)
                    tag['value'] = corrected_street_name

                if tag['key'] == 'phone':
                    phone_number = tag['value']
                    corrected_phone_number = update_phone_number(phone_number)
                    tag['value'] = corrected_phone_number
                    
                if tag['key'] == 'postcode':
                    post_code = tag['value']
                    corrected_post_code = update_post_code(post_code)
                    tag['value'] = corrected_post_code
                    
                if tag['key'] == 'state':
                    state_value = tag['value']
                    corrected_state_value = update_state_name(state_value)
                    tag['value'] = corrected_state_value
                    
                if tag['key'] == 'city':
                    city_value = tag['value']
                    corrected_city_value = update_city_name(city_value)
                    tag['value'] = corrected_city_value
                    
                if tag:
                    tags.append(tag)

            #processes way node child tags          
            elif child.tag == 'nd':
                
                #assign top level element id
                way_node['id'] = element.attrib['id']
                
                #assign ref tag to 'node_id' key
                way_node['node_id'] = child.attrib['ref']
                
                #assigns a position based on the length of the currently forming dict
                way_node['position'] = len(way_nodes)
                if way_node:
                    way_nodes.append(way_node)
		            
            else:
                continue
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}
        
# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()

def process_child_tag_colon(element, child, default_tag_type, tag):
    
    #The two below regular expressions give the values before and after the colon
    re_before_colon = re.compile(r'(^([a-z]|_)+):')
    re_after_colon = re.compile(r'(:([a-z]|_)+)?(:([a-z]|_)+)')
    
    #the two below statements set the variables to the characters before and after the colon
    tag_type_value = (re_before_colon.search(child.attrib['k'])).group()[:-1]
    tag_key_value = ((re_after_colon.search(child.attrib['k'])).group())[1:]
    
    tag['key'] = tag_key_value
    
    if tag_type_value:
        tag['type'] = tag_type_value
    else:
        tag['type'] = default_tag_type
    
    #tag ID uses the top level node id attribute value    
    tag['id'] = element.attrib['id']
    tag['value'] = child.attrib['v']
    
    return tag

def process_regular_child_tag(element, child, default_tag_type, tag):
    
    tag['value'] = child.attrib['v']
    tag['key'] = child.attrib['k']
    tag['type'] = default_tag_type
    tag['id'] = element.attrib['id']
    return tag

def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        raise Exception(message_string.format(field, error_string))

#Checks the street type, and updates the value if necessary, based on expected and mapping structures found at the top of the file
def update_street_name(name, mapping):
    original_format = street_type_re.search(name)
    street_type = original_format.group()
    if street_type not in expected:
        name = re.sub(street_type_re, mapping[street_type], name)
    return name

def update_phone_number(name):
    #The below statement strips non-digit characters from each phone number
    clean_number = re.sub(r'[^0-9]+', '', name)
    #removes the country code if it is there
    if clean_number[:1] == '1':
        clean_number = clean_number[1:]
    #standardizes the formatting of each phone number
    clean_number = clean_number[:3] + "-" + clean_number[3:6] + "-" + clean_number[6:]      
    return clean_number

def update_city_name(name):
    #regular expression returns only the first word, the city, not the second word, the state, if it is present
    original_city = city_type_re.search(name)
    if original_city:
        name = original_city.group()             
        #There was one case where the above did not work, the below corrects this exception
        if name == 'Round':
            name = "Round Rock"      
    return name

#The regular expression for this function returns only the first 5 digits
def update_post_code(name):
    name = post_code_re.search(name)
    name = name.group()
    return name

#Standardizes all values to Texas for the state field
def update_state_name(name):
    if name == "TX":
        name = "Texas"
    return name


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])

if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=True)
