# - * - coding=utf-8 -*-
import cv2
import numpy as np

SPREAD_WIDTH = 5
STRENGTH = 5


# 返回value对应的二进制字符串
# 其中value是要转化的整数
# bitsize是转化为字符串的长度
# bin_value(6, 8)将整数6转化为长度为8的二进制'00000110'
def bin_value(value, bitsize=8):
    binval = bin(value)[2:]
    if len(binval) > bitsize:
        print("Larger than the expected size")
    while len(binval) < bitsize:
        binval = "0" + binval
    return binval


def spread_spectrum(bit_string, spread_width):
    ret = ""
    for bit in bit_string:
        ret += bit * spread_width
    return ret


def get_original_bin(bit_string, spread_width):
    if len(bit_string) % spread_width != 0:
        print("长度错误，需是%d整数倍。" % spread_width)
        return None
    ret_string = ""
    for i in range(int(len(bit_string) / spread_width)):
        count = 0
        for j in range(spread_width):
            count += int(bit_string[i * spread_width + j])
        if count < spread_width * 0.6:
            ret_string += "0"
        else:
            ret_string += "1"
    return ret_string


def watermark_encode(watermark_string):
    # 初始化水印信息
    watermark = ""
    # 水印字符串长度转化为32bits的二进制字符串并加入水印信息中
    watermark_size = bin_value(len(watermark_string), 8)
    watermark += spread_spectrum(watermark_size, SPREAD_WIDTH)
    # 循环转化字符串中的字符为二进制字符串并加入+水印信息中
    for char in watermark_string:
        temp_string = bin_value(ord(char))
        watermark += spread_spectrum(temp_string, SPREAD_WIDTH)
    return watermark


def embed_bit(bit, dcted_block, alpha):
    if bit == 1:
        if dcted_block[2, 1] < dcted_block[1, 2]:
            dcted_block[2, 1], dcted_block[1, 2] = dcted_block[
                1, 2], dcted_block[2, 1]
            if dcted_block[2, 1] - dcted_block[1, 2] < alpha:
                dcted_block[2, 1] += alpha
        elif dcted_block[2, 1] == dcted_block[1, 2]:
            dcted_block[2, 1] += alpha
    elif bit == 0:
        if dcted_block[2, 1] > dcted_block[1, 2]:
            dcted_block[2, 1], dcted_block[1, 2] = dcted_block[
                1, 2], dcted_block[2, 1]
            if dcted_block[1, 2] - dcted_block[2, 1] < alpha:
                dcted_block[2, 1] -= alpha
        elif dcted_block[2, 1] == dcted_block[1, 2]:
            dcted_block[2, 1] -= alpha
    else:
        print("请输入正确的水印值，0或1。")


def extract_bit(dcted_block):
    if dcted_block[2, 1] > dcted_block[1, 2]:
        return 1
    else:
        return 0


def embed_watermark(image_path, watermark_string, embeded_image_path):
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)

    image = cv2.cvtColor(image, cv2.COLOR_BGR2YCR_CB)
    img = image[:, :, 0]

    watermark = watermark_encode(watermark_string)
    iHeight, iWidth = img.shape

    countHeight = int(iHeight / 8)
    countWidth = int(iWidth / 8)

    # 初始化空矩阵保存量化结果
    img2 = np.empty(shape=(iHeight, iWidth))
    index = 0
    # 分块DCT
    for startY in range(0, countHeight * 8, 8):
        for startX in range(0, countWidth * 8, 8):
            block = img[startY:startY + 8, startX:startX + 8].reshape((8, 8))
            # 进行DCT
            blockf = np.float32(block)
            block_dct = cv2.dct(blockf)
            if index < len(watermark):
                embed_bit(int(watermark[index]), block_dct, STRENGTH)
                index += 1

            block_idct = cv2.idct(block_dct)

            for y in range(8):
                for x in range(8):
                    img[startY + y, startX + x] = block_idct[y, x]

    image = cv2.cvtColor(image, cv2.COLOR_YCR_CB2BGR)
    cv2.imwrite(embeded_image_path, image)


def extract_watermark(embeded_image_path):
    # 读取含密图像并将其转换为YCrCb颜色空间
    image = cv2.imread(embeded_image_path, cv2.IMREAD_COLOR)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2YCR_CB)
    img = image[:, :, 0]  # 提取Y通道（亮度）

    iHeight, iWidth = img.shape
    countHeight = int(iHeight / 8)  # 计算图像垂直方向上8x8块的数量
    countWidth = int(iWidth / 8)    # 计算图像水平方向上8x8块的数量
    index = 0                       # 初始化索引，用于跟踪处理的图像块数量
    length_string = ""              # 初始化字符串，用于存储水印长度信息
    watermark_length = 0            # 初始化变量，用于存储提取的水印长度
    watermark_string = ""           # 初始化字符串，用于存储提取的水印二进制信息

    # 通过嵌套循环遍历图像的每一个8x8块
    for startY in range(0, countHeight * 8, 8):
        for startX in range(0, countWidth * 8, 8):
            # 提取当前8x8块
            block = img[startY:startY + 8, startX:startX + 8].reshape((8, 8))
            
            # 对块进行离散余弦变换（DCT）
            blockf = np.float32(block)
            block_dct = cv2.dct(blockf)

            # 在前8 * SPREAD_WIDTH个图像块中，提取水印长度信息
            if index < 8 * SPREAD_WIDTH:
                bit = extract_bit(block_dct)
                if bit == 1:
                    length_string += "1"
                else:
                    length_string += "0"
                # 当处理完8 * SPREAD_WIDTH个图像块时，解码长度信息字符串
                if index == 8 * SPREAD_WIDTH - 1:
                    length_string = get_original_bin(length_string, SPREAD_WIDTH)
                    watermark_length = int(length_string, 2)
                index += 1

            # 在剩余的图像块中（即在前8 * SPREAD_WIDTH个图像块之后），提取水印信息
            elif index < 8 * SPREAD_WIDTH + watermark_length * 8 * SPREAD_WIDTH:
                bit = extract_bit(block_dct)
                if bit == 1:
                    watermark_string += "1"
                else:
                    watermark_string += "0"
                # 当提取完所有水印信息后，解码水印字符串
                if index == 8 * SPREAD_WIDTH + watermark_length * 8 * SPREAD_WIDTH - 1:
                    watermark_string = get_original_bin(watermark_string, SPREAD_WIDTH)
                    decoded_watermark = ""
                    # 从水印二进制信息中解码每个字符
                    for i in range(watermark_length):
                        decoded_watermark += chr(int(watermark_string[i * 8:(i + 1) * 8], 2))
                    # 打印解码后的水印并返回
                    print(decoded_watermark)
                    return decoded_watermark
                index += 1



#if __name__ == '__main__':
    #extract_watermark(
    #    "C:/Users/admin/Desktop/learn_flask_the_hard_way/0x08_adminlte/instance/temp/temp.jpg"
    #)
    