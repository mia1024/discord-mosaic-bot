FROM python:3.9-alpine AS deps
WORKDIR /

RUN apk update && apk add --no-cache build-base cmake libffi-dev openjpeg-dev libjpeg-turbo-dev libpng-dev libwebp-dev openblas-dev tiff-dev unzip curl openjpeg rsync

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV CFLAGS="-g0 -s -O3 -fomit-frame-pointer -flto"

RUN mkdir /mosaic_bot
RUN python -m venv /mosaic_bot/env
RUN /mosaic_bot/env/bin/python -m pip install wheel numpy --compile

RUN curl -o cv.zip https://codeload.github.com/opencv/opencv/zip/3.4.13 
RUN unzip -q cv.zip
RUN mkdir build cv-dist
WORKDIR build
RUN cmake -DBUILD_LIST=imgproc,core,python3 -DPYTHON3_EXECUTABLE=/mosaic_bot/env/bin/python -DWITH_CSTRIPES=ON -DCMAKE_INSTALL_PREFIX=/cv-dist /opencv-3.4.13/ 
RUN make -j$(nproc)
RUN make install -j$(nproc)
RUN rm -r /cv-dist/include/ /cv-dist/share/
RUN rsync -rauv /cv-dist/ /mosaic_bot/env/
RUN /mosaic_bot/env/bin/python -m pip install discord aiohttp cchardet requests pillow flask sqlalchemy  --compile

RUN mkdir source
WORKDIR /source
COPY . /source/

ARG MOSAIC_BUILD_HASH
ENV MOSAIC_BUILD_HASH=$MOSAIC_BUILD_HASH
RUN python build_docker.py
RUN /mosaic_bot/env/bin/python -m pip install /source --compile
RUN ln -s /bot/credentials.py "/mosaic_bot/env/lib/python3.9/site-packages/mosaic_bot/credentials.py"

WORKDIR /mosaic_bot
RUN mkdir data

FROM python:3.9-alpine
RUN apk update && apk add --no-cache libffi openjpeg libjpeg-turbo libpng libwebp openblas tiff libstdc++
COPY --from=deps --chown=1000:1000 /mosaic_bot /bot
#COPY --from=deps /cv-dist/ /bot/env/
USER 1000:1000
WORKDIR /bot
ENV DATA_PATH=/bot/data
ENV LD_LIBRARY_PATH=/bot/env/lib64
ENV PATH=/bot/env/bin
ENTRYPOINT /bot/env/bin/python -m mosaic_bot
