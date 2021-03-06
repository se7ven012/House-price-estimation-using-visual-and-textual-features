# import the necessary packages
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input
from tensorflow.keras.layers import Dense
from tensorflow.keras.layers import Flatten
from tensorflow.keras.layers import Conv2D
from tensorflow.keras.layers import BatchNormalization
from tensorflow.keras.layers import Activation
from tensorflow.keras.layers import AveragePooling2D
from tensorflow.keras.layers import Dropout
from tensorflow.keras.layers import add
from tensorflow.keras.regularizers import l2
from tensorflow.keras import optimizers

# for cuDNN debug
from tensorflow.compat.v1 import ConfigProto
from tensorflow.compat.v1 import InteractiveSession

config = ConfigProto()
config.gpu_options.allow_growth = True
session = InteractiveSession(config=config)
# for cuDNN debug


def create_mlp(dim, regress=False):
	inputs = Input(shape=dim)
	v = Dense(8, activation='relu')(inputs)
	v = Dense(16, activation='relu')(v)
	v = Dense(4, activation='relu')(v)

	if regress:
		v = Dense(1, activation="linear")(v)

	model = Model(inputs=inputs, outputs=v)
	return model

optmz = optimizers.Adam(lr=0.001)

def resLyr(
    inputs,
    numFilters=16,
    kernelSz=3,
    strides=1,
    activation="relu",
    batchNorm=True,
    convFirst=True,
    lyrName=None,
):

    convLyr = Conv2D(
        numFilters,
        kernel_size=kernelSz,
        strides=strides,
        padding="same",
        kernel_initializer="he_normal",
        kernel_regularizer=l2(1e-4),
        name=lyrName + "_conv" if lyrName else None,
    )
    x = inputs

    if convFirst:
        x = convLyr(x)

        if batchNorm:
            x = BatchNormalization(name=lyrName + "_bn" if lyrName else None)(x)

        if activation is not None:
            x = Activation(
                activation, name=lyrName + "_" + activation if lyrName else None
            )(x)
    else:
        if batchNorm:
            x = BatchNormalization(name=lyrName + "_bn" if lyrName else None)(x)

        if activation is not None:
            x = Activation(
                activation, name=lyrName + "_" + activation if lyrName else None
            )(x)

        x = convLyr(x)
    return x


# ResBlock
def resBlkV1(inputs, numFilters=16, numBlocks=3, downsampleOnFirst=True, names=None):

    x = inputs

    for run in range(0, numBlocks):
        strides = 1
        blkStr = str(run + 1)

        if downsampleOnFirst and run == 0:
            strides = 2

        y = resLyr(
            inputs=x,
            numFilters=numFilters,
            strides=strides,
            lyrName=names + "_Blk" + blkStr + "_Res1" if names else None,
        )
        y = resLyr(
            inputs=y,
            numFilters=numFilters,
            activation=None,
            lyrName=names + "_Blk" + blkStr + "_Res2" if names else None,
        )

        if downsampleOnFirst and run == 0:
            x = resLyr(
                inputs=x,
                numFilters=numFilters,
                kernelSz=1,
                strides=strides,
                activation=None,
                batchNorm=False,
                lyrName=names + "_Blk" + blkStr + "_lin" if names else None,
            )

        x = add([x, y], name=names + "_Blk" + blkStr + "_add" if names else None)
        x = Activation(
            "relu", name=names + "_Blk" + blkStr + "_relu" if names else None
        )(x)

    return x


def createResNetV1(width, height, depth, regress=False):
    inputShape = (height, width, depth)
    chanDim = -1
    inputs = Input(shape=inputShape)

    v = resLyr(inputs, lyrName="Inpt")
    v = resBlkV1(
        inputs=v, numFilters=16, numBlocks=3, downsampleOnFirst=False, names="Stg1"
    )
    v = resBlkV1(
        inputs=v, numFilters=32, numBlocks=3, downsampleOnFirst=True, names="Stg2"
    )
    v = resBlkV1(
        inputs=v, numFilters=64, numBlocks=3, downsampleOnFirst=True, names="Stg3"
    )
    v = AveragePooling2D(pool_size=8, name="AvgPool")(v)
    v = Flatten()(v)
    v = Dense(16, activation="relu")(v)
    v = BatchNormalization(axis=chanDim)(v)
    v = Dropout(0.5)(v)
    v = Dense(4, activation="relu")(v)

    if regress:
        v = Dense(1, activation="linear")(v)

    model = Model(inputs=inputs, outputs=v)
    return model

