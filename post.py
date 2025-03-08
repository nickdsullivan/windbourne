import requests

# Define the URL
url = "https://windbornesystems.com/career_applications.json"

# Define the data to be sent in the POST request
data = {
    "message": "Hello,",
    "email": "nickdsullivan@gmail.com",
}

# Send the POST request
response = requests.post(url, data=data)

# Check if the request was successful
if response.status_code == 200:
    print("Request successful!")
    print(response.json())  # Assuming the server responds with JSON data
else:
    print(f"Request failed with status code {response.status_code}")
    print(response.text)  # Print the error message
