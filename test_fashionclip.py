
from fashion_clip.fashion_clip import FashionCLIP
import numpy as np
import os
import time
fclip = FashionCLIP('fashion-clip')

text = ["a shirt with a star"]
text_embeddings = fclip.encode_text(text, batch_size=32)
text_embeddings = text_embeddings/np.linalg.norm(text_embeddings, ord=2, axis=-1, keepdims=True)

image=[]
for i in range(1,10):
    filepath = f'./image/image{i}.jpg'
    if os.path.exists(filepath):
        image.append(filepath)

start_time = time.time()
image_embeddings = fclip.encode_images(image, batch_size=32)
end_time = time.time()
print('time: ', round(end_time - start_time, 2))
image_embeddings = image_embeddings/np.linalg.norm(image_embeddings, ord=2, axis=-1, keepdims=True)
dot_product_single = np.dot(image_embeddings, text_embeddings.T)

# return 10 matching products
indecies = np.flip(dot_product_single.argsort(0)[-10:]).flatten().tolist()
for i in indecies:
    print(image[i])