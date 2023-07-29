
import numpy as np
import cv2
import chardet
import matplotlib.pyplot as plt
import os


"""
最新更新 : 可以支持彩色图啦 !! ( RGB 彩色图在 B 中通道中隐写信息)
建议投喂 png 或 jpg 格式图像 (想支持更多的,修改一下 process_image 函数即可 )

此文件功能是嵌入文本信息到图片像素值的 LSB 位中,包括以下函数:

str_2_bin & bin_2_str : 实现字符串和二进制互相转换
bin_2_num & num_2_bin : 实现二进制和十进制数的转换,十进制数字用户记录文本长度
check_charset : 如果要将 txt 文档里的内容隐写到图片上, 此函数检查文档的编码格式
process_image : 如果接收 jpg(jpeg) 图像, 直接转换为 png, 方便统一操作
LSB_reset : 将 0/1 隐写到像素点的 LSB 位
embed_from_str : 调用 LSB_reset, 将自定义的字符串变量隐写到图片里
embed_from_file : 调用 LSB_reset, 将 txt 文档里的内容隐写到图片里
extract_watermark : 按照正确的长度提取隐写的信息

LSB 提取隐写信息的时候,经常遇到的问题就是,不知道在哪里该停止读取,
这样一来经常出现 正常文本 + 后面全是乱码 的情形,为了解决这个问题,
我给的设计是 : 将待嵌入的 0/1 的长度用 16 个比特位来记录
(这样一来最大嵌入容量为 65536 bit, 如果想要嵌入更大容量,手动修改一下即可)
此 16 bit 放到待嵌入 0/1 之前,提取的时候,先只提取前 16 bit,得到后面的文本长度
然后以此长度进行正确的提取即可,这样得到的就只有原有的信息,就不会出现乱码
"""


def str_2_bin(s: str) -> str:
    return ''.join([bin(b)[2:].zfill(8) for b in s.encode('utf-8')])


def bin_2_str(b: str) -> str:
    return b''.join([int(b[i:i+8], 2).to_bytes(1, 'big')
                     for i in range(0, len(b), 8)]).decode('utf-8')


def bin_2_num(s):
    c = 0
    for i in range(16):
        if s[i] == '0':
            t = 0
        else:
            t = 1
        c += t * 2 ** (15-i)
    return c


def num_2_bin(n):
    return bin(n).replace('0b', '').zfill(16)


def check_charset(file_path):
    with open(file_path, "rb") as f:
        data = f.read(32)
        charset = chardet.detect(data)['encoding']
    return charset


# 如果是 png 图像, 则不做改变, 如果是 jpg 图像,则转换为 png
def process_image(image_path):
    # Check if the input image exists
    if not os.path.exists(image_path):
        raise FileNotFoundError("The input image does not exist.")

    # Check the image format (png, jpg, jpeg)
    _, file_extension = os.path.splitext(image_path)
    file_extension = file_extension.lower()

    if file_extension == '.png':
        # If the image is already in png format, read and return it
        img = cv2.imread(image_path)
        return img
    elif file_extension in ('.jpg', '.jpeg'):
        # If the image is jpg or jpeg, convert it to png and then read and return it
        img = cv2.imread(image_path)
        new_image_path = os.path.splitext(image_path)[0] + '.png'
        cv2.imwrite('./temp/t.png', img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        converted_img = cv2.imread('./temp/t.png')
        os.remove('./temp/t.png')
        return converted_img
    else:
        raise ValueError("Unsupported image format.")


def LSB_reset(img, secret):
    height = img.shape[0]
    width = img.shape[1]
    cp = img.copy()
    u = np.empty([height, width], dtype=int)
    for i in range(height):
        for j in range(width):
            u[i, j] = img[i, j][0]
    carrier = u.ravel()
    if len(carrier) < len(secret):
        print('the iamge is too small to carry your information.')
        return
    else:
        for i in range(len(secret)):
            if carrier[i] % 2 == 1 and secret[i] == '0':
                carrier[i] -= 1
            if carrier[i] % 2 == 0 and secret[i] == '1':
                carrier[i] += 1
        carrier.resize(height, width)
        print(len(secret), ' pixels have been influenced')
        for h in range(height):
            for w in range(width):
                cp[h, w][0] = carrier[h, w]
        return cp


# 参数为 : 载体图片路径,txt文件路径,保存到哪个路径
def embed_from_str(img_path, message, save_path):
    img = process_image(img_path)

    # 这里将内容长度编码为16比特,放到待嵌入比特之前
    Bs = message.encode("utf-8")
    bins = str_2_bin(message)
    addition = num_2_bin(len(Bs))
    to_be_put = addition + bins

    marked = LSB_reset(img, to_be_put)
    cv2.imwrite(save_path, marked)


# 参数为 : 载体图片路径,txt文件路径,保存到哪个路径
def embed_from_file(img_path, file_path, save_path):
    img = process_image(img_path)

    # with open(file_path, encoding=check_charset(file_path)) as f:
    # 这里最好使用上面被注释的语句,它可以检测文本的编码方式,我这里是utf-8,所以下面直接这样写了
    with open(file_path, encoding="utf-8") as f:
        words = f.read()
    Bs = words.encode("utf-8")
    bins = str_2_bin(words)
    addition = num_2_bin(len(Bs))
    to_be_put = addition + bins
    marked = LSB_reset(img, to_be_put)
    cv2.imwrite(save_path, marked)


# 提取水印信息
def extract_watermark(img_path):
    img = cv2.imread(img_path)
    height = img.shape[0]
    width = img.shape[1]
    u = np.empty([height, width], dtype=int)
    for i in range(height):
        for j in range(width):
            u[i, j] = img[i, j][0]
    lined = u.ravel()
    l = ''
    m = ''
    # 首先提取前 16 位,获知内容长度
    for i in range(16):
        if lined[i] % 2 == 0:
            l += '0'
        else:
            l += '1'
    length = bin_2_num(l)

    for i in range(16, length*8 + 16):
        if lined[i] % 2 == 0:
            m += '0'
        else:
            m += '1'
    message = bin_2_str(m)
    print("\n----------  info extracted :  ----------\n")
    print(message)
    return message


# ------------ 以下为测试内容 -------------

# 测试嵌入字符串 ~

# embed_from_str('./c8/lena.png', 'hello world , 你好, 火星 !', './out/lllenaaa.png')
# extract_watermark('./out/lllenaaa.png')


# embed_from_str('./g12/01.png', 'hello world , 你好, 火星 !', './out/lnn.png')
# extract_watermark('./out/lnn.png')


# embed_from_str('./pics/lena.jpg', 'hello world , 你好, 火星 !', './out/tktkkk.png')
# extract_watermark('./out/tktkkk.png')


# # 测试嵌入txt文本信息 ~
#embed_from_file('./pics/lena.jpg', './txts/lemon.txt', './out/ajaxff.png')
#extract_watermark('./out/ajaxff.png')
