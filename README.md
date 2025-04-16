# KinderKasse
Kinderkasse mit Scanner, BA63-Display und Bon-Drucker

# Sources
https://github.com/CatCookie/VFDSerial

# BOM 
Raspberry Pi
Handscanner Netum NSL5 

## RS232 Shield einrichten

https://www.waveshare.com/wiki/RS485_RS232_HAT#Add_driver

```
sudo nano /boot/firmware/config.txt
#Add the following, int_pin is set according to the actual welding method:
dtoverlay=sc16is752-spi1,int_pin=24
#reboot device
sudo reboot
```


## Scanner einrichten

Wir binden den Scanner per id ein. 
```bash
ls -l /dev/serial/by-id/
```
Dies dann hier ändern
```bash
SCANNER_DEVICE = '/dev/serial/by-id/usb-Barcode_Scanner_SN1234567-if00'
```


Der Scanner muss als COM-Device konfiguriert werden. 

![grafik](https://github.com/user-attachments/assets/692d69e5-d2de-45a3-ac9b-fac8e6df6d1c)

Für die Eltern, kann der Beep über diese Codes gesteuert werden: 

BEEP EIN

![grafik](https://github.com/user-attachments/assets/75567ca1-f730-4e01-b75b-60c989fc5fbb)


BEEP AUS

![grafik](https://github.com/user-attachments/assets/245ae556-e9b5-4f14-b018-279da3492066)


Lautstärke LEISE

![grafik](https://github.com/user-attachments/assets/41e276c0-c899-4ab6-ab72-8fe2dfd1a5b1)




