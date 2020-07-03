FROM balenalib/raspberry-pi:buster
MAINTAINER tomas

# TODO unused but will be /status or /health
EXPOSE 5000

# install libs
RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y \
      build-essential \
      cmake \
      unzip \
      pkg-config \
      libjpeg-dev \
      libpng-dev \
      libtiff-dev \
      libavcodec-dev \
      libavformat-dev \
      libswscale-dev \
      libv4l-dev \
      libxvidcore-dev \
      libx264-dev \
      libgtk-3-dev \
      libatlas-base-dev \
      gfortran \
      python3-pkg-resources \
      python3-dev \
      python3-pip && \
    pip3 install --upgrade pip && \
    apt-get clean

# install numpy, opencv src
COPY libs/opencv-4.0.0.zip /opt
COPY libs/opencv_contrib-4.0.0.zip /opt
# version is duplicated in requirements.txt, but we dont want to invalidate image cache when python libs are changed
RUN pip3 install 'numpy==1.17.4' && \
    cd /opt && \
    unzip opencv-4.0.0.zip &&  ln -sv /opt/opencv-4.0.0 /opt/opencv && \
    unzip opencv_contrib-4.0.0.zip && ln -sv /opt/opencv_contrib-4.0.0 /opt/opencv_contrib

# compile opencv
RUN cd /opt/opencv && \
    mkdir build && \
    cd build && \
    cmake -D CMAKE_BUILD_TYPE=RELEASE \
      -D CMAKE_INSTALL_PREFIX=/usr/local \
      -D OPENCV_EXTRA_MODULES_PATH=/opt/opencv_contrib/modules \
      -D ENABLE_NEON=ON \
      -D ENABLE_VFPV3=ON \
      -D BUILD_TESTS=OFF \
      -D OPENCV_ENABLE_NONFREE=ON \
      -D INSTALL_PYTHON_EXAMPLES=OFF \
      -D BUILD_EXAMPLES=OFF .. && \
    pwd && \
    make -j4 && \
    make install && \
    ldconfig && \
    ln -sv /usr/local/python/cv2/python-3.7/cv2.cpython-37m-arm-linux-gnueabihf.so  /usr/local/lib/python3.7/dist-packages/cv2.so


WORKDIR /app
COPY requirements.txt /app
RUN pip3 install -r requirements.txt
COPY src /app

CMD [ "python3", "-u", "main.py" ]
