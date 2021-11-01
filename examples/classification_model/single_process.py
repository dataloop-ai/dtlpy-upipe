import torchvision.models as models
import torchvision.datasets
import numpy as np
import torch
import time
import cv2

testset = torchvision.datasets.CIFAR10(root='./data',
                                       train=False,
                                       download=True,
                                       transform=None)
inception = models.inception_v3(pretrained=True, transform_input=True)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f'device is {device}')
inception.to(device)
inception.eval()

counter = 0
tic = time.time()
while True:
    pil_image, label = testset[np.random.randint(0, len(testset))]
    image = np.asarray(pil_image)
    # print(f'reading label {label}')
    ########################
    norm_image = cv2.resize(image, (256, 256)).transpose((2, 0, 1)) / 255
    pred = inception(torch.from_numpy(norm_image).unsqueeze(0).to(device).float())
    # print(f"prediction is {np.argmax(pred.cpu().detach().numpy())}")

    if counter % 100 == 0:
        print(f"counter: {counter / 1000}K, FPS: {counter / (time.time()-tic)}")

    counter += 1
