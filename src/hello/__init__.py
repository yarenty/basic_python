import os
import time

def main():
    print("Hello world");
    print(os.path.curdir);
    print(time.time());
    # fd = os.open("filename.txt", 777);
    # print(os.read(fd, 1024));
    # os.write(fd,"yooho");
    # os.close(fd)
    print('What is your name?');
    myName = input();
    print('It is good to meet you, ' + myName);
    print("hmmm..");

main()
