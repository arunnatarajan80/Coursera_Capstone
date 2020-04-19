# import libraries
import pandas as pd
import numpy as np
import requests
import geocoder
from geopy.geocoders import Nominatim
import os

# Function to gather Latitude and Longitude Coordinates of given neighborhoods
def getLocation(row, city='coimbatore'):
    geolocator = Nominatim(user_agent="my-application")
    loc = geolocator.geocode('{}, {}'.format(row['Neighborhood'], city))
    if loc:
        row['Latitude'] = loc.latitude
        row['Longitude'] = loc.longitude
    else:
        row['Latitude'] = None
        row['Longitude'] = None

    return row

# Function to gather venue name, location and category
# endpoint can be either 'explore' or 'search'
def getNearbyVenues_Multi(endpoint, names, latitudes, longitudes):
    
    # Foursquare API Setup
    CLIENT_ID = os.environ.get("FS_CLIENT_ID")
    CLIENT_SECRET = os.environ.get("FS_CLIENT_SECRET")
    VERSION = '20180605' # Foursquare API version
    LIMIT = 500
    radius = 500

    venues_list=[]
    for name, lat, lng in zip(names, latitudes, longitudes):
        #print(name)
            
        # create the API request URL
        urlFormatter = 'https://api.foursquare.com/v2/venues/{}?&client_id={}&client_secret={}&v={}&ll={},{}&radius={}&limit={}'
        url = urlFormatter.format(endpoint,
            CLIENT_ID, 
            CLIENT_SECRET, 
            VERSION, 
            lat, 
            lng, 
            radius, 
            LIMIT)
            
        # make the GET request
        resp = requests.get(url)
        #print(resp)
        
        
        # return only relevant information for each nearby venue
        if(endpoint == 'explore'):
            groups = resp.json()["response"]['groups']
            for group in groups:
                venues_list.append([(
                    name, 
                    lat, 
                    lng, 
                    group['type'],
                    group['name'],
                    v['venue']['name'], 
                    v['venue']['id'], 
                    v['venue']['location']['lat'], 
                    v['venue']['location']['lng'],  
                    v['venue']['categories']) for v in group['items']]) # v['venue']['categories'][0]['name']
        else:
            venues = resp.json()["response"]['venues']
            venues_list.append([(
                name, 
                lat, 
                lng, 
                'Not Applicable', # Group Type column is not applicable for search end point
                'Not Applicable', # Group Name column is not applicable for search end point
                v['name'], 
                v['id'],
                v['location']['lat'], 
                v['location']['lng'],  
                v['categories']) for v in venues]) #  v['venue']['categories'][0]['name']

    nearby_venues = pd.DataFrame([item for venue_list in venues_list for item in venue_list])
    nearby_venues.columns = ['Neighborhood', 
                              'Neighborhood Latitude', 
                              'Neighborhood Longitude', 
                              'Recommendation Group Type',
                              'Recommendation Group Name',
                              'Venue', 
                              'Venue Id', 
                              'Venue Latitude', 
                              'Venue Longitude', 
                              'Venue Categories']
    
    # Create Venue Category Column and assign the first category from category list if not avaialble assign NONE
    nearby_venues['Venue Category'] = nearby_venues['Venue Categories'].apply(lambda vcl: vcl[0]['name'] if len(vcl) > 0 else None)
    nearby_venues.drop(columns=['Venue Categories'], inplace=True)
    
    return(nearby_venues)


# Function to recursively traverse through Foursquare Categories and collect all children in to a list 
def getChildCategoriesRecursive(categories):
    children = []
    for child in categories:
        children.append(child['name'])
        if 'categories' in child.keys():
            children.extend(getChildCategoriesRecursive(child['categories']))
    return children

# Function to collect Foursquare Top Level Categories and their sub-categories as DataFrame
def getFoursquareCategories():
    CLIENT_ID = os.environ.get("FS_CLIENT_ID")
    CLIENT_SECRET = os.environ.get("FS_CLIENT_SECRET")
    VERSION = '20180605' # Foursquare API version
    url = 'https://api.foursquare.com/v2/venues/categories?&client_id={}&client_secret={}&v={}'.format(
            CLIENT_ID, 
            CLIENT_SECRET, 
            VERSION)
    resp = requests.get(url)
    results = resp.json()["response"]

    categoryDf = pd.DataFrame(columns=['Top Category', 'Sub Category'])
    for topCat in results['categories']:
        children = []
        if 'categories' in topCat.keys():
            children = getChildCategoriesRecursive(topCat['categories'])
            
        toadd = {'Top Category':[topCat['name']]*len(children),
                'Sub Category':children}
        categoryDf = categoryDf.append(pd.DataFrame(toadd))
        
    return categoryDf