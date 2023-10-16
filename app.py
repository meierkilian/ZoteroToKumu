'''Creates a Kumu Import file from a Zotero Library'''
import json
import os
from pyzotero import zotero
from dotenv import load_dotenv
load_dotenv()

library_id: str = os.getenv("LIBRARY_ID")
library_type: str = os.getenv("LIBRARY_TYPE")
api_key: str = os.getenv("ZOTERO_API_KEY")

# Describe the structure of information
themeStructure: dict = {
    'Docking': [
        'FixedTarget',
        'GeneralDocking',
        { 'MovingTarget': [
            'GroundVehicle',
            'OtherMovingTarget',
            { 'AirbornVehicle': [
                'FixedWing-FixedWing',
                'RotaryWing-RotaryWing',
                'RotaryWing-FixedWing']
            }
            ]
        }
        ]
    }

def getSubElems(elem) :
    subElems: list = []
    if type(elem) is dict:
        for key in elem:
            subElems.append(key)
            subElems += getSubElems(elem[key])
    elif type(elem) is list:
        for e in elem:
            subElems += getSubElems(e)
    else:
        subElems.append(elem)
    return subElems

allThemes = getSubElems(themeStructure)

zot: zotero.Zotero = zotero.Zotero(library_id=library_id,
                                   library_type=library_type,
                                   api_key=api_key)
items: dict = zot.top(limit=5000)
json_data: dict[str,list] = {'elements':[], 'connections':[]}
item_count: int = 1
total_items: int = len(items)


for theme in allThemes:
    json_data['elements'].append({'label':theme, 'type':'Theme'})


def createSubConnections(elem):
    names = []
    if type(elem) is dict:
        for e in elem:
            for child in elem[e]:
                if type(child) is dict:
                    json_data['connections'].append({'from':e, 'to':list(child.keys())[0], 'type':'InTheme'})
                    createSubConnections(child)
                else:
                    json_data['connections'].append({'from':e, 'to':child, 'type':'InTheme'})
    
    return names

createSubConnections(themeStructure)

# Iterate across items in the Zotero Library
for item in items:
    # Create variables to store attributes of the item
    try:
        label: str = str(item['data']['title'])
        url: str = str(item['data'].get('url', ""))
        href: str = item['links']['self'].get('alternate', "")
        desc: str = str(item['data'].get('abstractNote', ""))
        item_type: str = str(item['data'].get('itemType', ""))
        pdate: str = str(item['data'].get('date', ""))
        publication: str = str(item['data'].get('publicationTitle', ""))        
        all_tags: list = list(item['data'].get('tags', ""))


        all_tags_dict = []
        for t in all_tags:
            all_tags_dict.append(dict(t))

        relevant_tags: list = []
        for t in all_tags_dict:
            if 'type' not in t:
                relevant_tags.append(t['tag'])



        # Create a kumu node for the item
        json_data['elements'].append({'label':label,
                                      'type':item_type,
                                      'Zotero Link':href,
                                      'Original Link':url,
                                      'Description':desc,
                                      'Publication':publication,
                                      'Date':pdate,
                                      'Tag':relevant_tags
                                      })

        if 'creators' in item['data']:
            # Add authors of the item as Elements and connect them to the item with an Edge
            for creator in item['data']['creators']:
                author_name = creator.get('firstName',"---") + " " + creator.get('lastName',"---")
                json_data['elements'].append({'label':author_name, 'type':'Person'})
                json_data['connections'].append({'from':author_name, 'to':label, 'type':'Authorship'})

        for tag in relevant_tags:
            if tag in allThemes:
                json_data['connections'].append({'from':tag, 'to':label, 'type':'InTheme'})            

        print(str(item_count) + "/" + str(total_items) + " - ", item['data']['title'])
        item_count += 1
        
    except Exception as e:
        print("---------------FISHY ITEM---------------")
        print(item)

# Write the JSON data to a file
with open('zotero.json', 'w',encoding='utf-8') as outfile:
    json.dump(json_data, outfile, indent=4)
