from pathlib import Path
import LSb_appli
import requests
from bs4 import BeautifulSoup
import os
#from image import embed_watermark


def send_post(username, password, text, file_path, url):
    s = requests.session()

    r = s.get(url + '/auth/login')
    soup = BeautifulSoup(r.text, 'html.parser')

    csrf_token = soup.find(id="csrf_token")['value']

    params = {
        'email': username,
        'password': password,
        'csrf_token': csrf_token
    }
    r = s.post(url + '/auth/login', data=params)
    if not r.status_code == 200:
        print('Login failed.')
        return

    image = Path(file_path)
    from_data = {'text': text}
    file = {'image': (image.name, open(image, 'rb'))}

    r = s.post(url + '/api/posts', data=from_data, files=file)
    if r.status_code < 200 or r.status_code >= 300:
        print('Upload post failed.')
        return


if __name__ == '__main__':
    username = 'ldy9321@cuc.edu.cn'
    password = 'Qh461300'

    text = 'test3'
    image_file = r'./img/s.png'
    url = 'http://127.0.0.1:5000'

    new_image = Path(image_file).with_name('embed.png')

    output_dir=r'./watermark/'
    
    LSb_appli.save_text_to_file('helloworld', output_dir)
    LSb_appli.embed_from_file(image_file, output_dir+'output.txt', str(new_image))
    #embed_watermark(image_file, 'helloworld', str(new_image))

    send_post(username, password, text, str(new_image), url)
