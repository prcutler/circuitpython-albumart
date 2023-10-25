from PIL import Image


img = Image.open("divinefits300.bmp")
img.quantize(colors=16, method=2)
smol_img = img.resize((64, 64))
convert = smol_img.convert(mode="P", palette=Image.WEB)
convert.save("divinefits64.bmp")