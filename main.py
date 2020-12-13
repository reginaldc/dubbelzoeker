# This Python file uses the following encoding: utf-8
import sys
import os
import hashlib
import sqlite3
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QDialog, QMessageBox, QFileDialog, QApplication
from formdubbelzoeker import *
from customextension import *
from functools import partial
import csv
import shutil

class Dubbelzoeker(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_dubbelzoeker()
        self.ui.setupUi(self)
        self.showMaximized()
        self.dbname = "dubbels.db"
        self.mydb = ""
        cwd = os.getcwd()
        self.db = cwd + '/' + self.dbname
        self.config = "dubbels.config"        
        self.connection = None
        self.primid = 0
        self.all = False
        self.init_db()       
        self.filetypes = []
        self.pic_ext = [".jpg", ".png", ".jpeg", ".bmp", ".gif"]
        self.vid_ext = [".avi", ".divx", ".mpg", ".mpeg", ".vob", ".m4v", ".mp4", ".flv", ".webm",\
        ".mov", ".wmv", ".mkv"]
        self.audio_ext = [".mp3",".wav",".flac",".ape",".wma",".ogg",".aac",".ac3"]
        self.document_ext = [".doc",".htm","html",".pdf", ".xps", ".cbz", ".epub",".azw",".azw3",".azw4",".cbr",".chm",\
            ".djvu",".djv",".docx",".fb2",".lit",".mobi",".pdb",".txt"]
        self.custom_ext = self.read_extensions()            
        self.dirlist = []
        self.dubbels = []
        self.keylist = ('ID', 'FILENAME', 'SIZE', 'SUM', 'NAME', 'EXT', 'ARCHIEF', 'VOLUME')
        self.ui.btnAddDir.clicked.connect(self.add_dir)
        self.ui.btnRemoveDir.clicked.connect(self.remove_dir)
        self.ui.checkPic.stateChanged.connect(self.check_pictures)
        self.ui.checkVid.stateChanged.connect(self.check_vids)
        self.ui.checkAudio.stateChanged.connect(self.check_audio)
        self.ui.checkDoc.stateChanged.connect(self.check_docs)
        self.ui.checkCustom.stateChanged.connect(self.check_custom)
        self.ui.checkAll.stateChanged.connect(self.check_all)
        self.ui.btnAangepast.clicked.connect(self.manage_custom_extensions)
        self.ui.btnScan.clicked.connect(self.scan_for_dubbels)
        self.ui.btnRemoveDubbele.clicked.connect(self.remove_dubbels)
        self.ui.lneArchief.textChanged.connect(self.check_lne_volume)
        self.ui.lneVolume.textChanged.connect(self.check_lne_archief)
        self.ui.btnLoadDb.clicked.connect(self.load_new_database)
        self.ui.btnSaveDb.clicked.connect(self.save_db)

    
    # database aanmaken als die niet bestaat
    def init_db(self):
        if not (os.path.exists("archief") and os.path.isdir("archief")):
            os.mkdir("archief")        
        dbexist = os.path.exists(self.db)
        if not dbexist:
            print("About to make database")
            self.connection = sqlite3.connect(self.db)
            self.ui.txtInfo.append("Database created and opened succesfully")
            c = self.connection.cursor()
            c.execute('''CREATE TABLE uniekebestanden
                (ID INT PRIMARY KEY     NOT NULL,
                FILENAME           TEXT    NOT NULL,
                SIZE            INT     NOT NULL,
                SUM        TEXT    NOT NULL,
                NAME       TEXT,
                EXT       TEXT,
                ARCHIEF         TEXT,
                VOLUME        TEXT);''')
            self.ui.txtInfo.append("Table created successfully")
            self.connection.commit()
            self.connection.close()
            self.primid = 1
        else:
            self.ui.txtInfo.append("using existing database")
            #get id of last record and assign it to primid
            self.connection = sqlite3.connect(self.db)
            cursor = self.connection.execute('SELECT max(ID) FROM uniekebestanden')
            max_id = cursor.fetchone()[0]
            if not max_id is None:
                self.primid = max_id + 1
            self.connection.close()

    def init_new_database(self):
        self.connection = sqlite3.connect(self.db)
        cursor = self.connection.execute('SELECT max(ID) FROM uniekebestanden')
        max_id = cursor.fetchone()[0]
        if not max_id is None:
            self.primid = max_id + 1
        self.connection.close()

    def save_db(self):
        db =  self.ui.lneSavedDb.text()
        if db:
            db = "archief/" + db + ".db"
            shutil.move(self.db, db)            

    def load_new_database(self):
        databasedir = os.getcwd() + '/archief'
        fname = QFileDialog.getOpenFileName(self, 'Open file', databasedir)
        if fname[0]:
            self.ui.lneDatabase.setText(fname[0])
            self.db = fname[0]
            self.init_new_database()

    def read_extensions(self):
        ext = []
        if os.path.exists('custom_extensions.csv'):
            with open('custom_extensions.csv', mode='r') as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')               
                for row in csv_reader:
                    ext = row
        return ext

    def check_all(self):
        if self.ui.checkAll.isChecked():
            self.ui.lstFiletype.clear()
            self.all = True
            self.ui.checkPic.setEnabled(False)
            self.ui.checkVid.setEnabled(False)
            self.ui.checkAudio.setEnabled(False)
            self.ui.checkDoc.setEnabled(False)
            self.ui.checkCustom.setEnabled(False)
        else:
            self.ui.checkPic.setEnabled(True)
            self.ui.checkVid.setEnabled(True)
            self.ui.checkAudio.setEnabled(True)
            self.ui.checkDoc.setEnabled(True)
            self.ui.checkCustom.setEnabled(True)
            self.ui.lstFiletype.addItems(self.custom_ext)
            
        
    def check_lne_volume(self):
        if len(self.ui.lneVolume.text()) > 0:
            self.ui.btnScan.setEnabled(True)

    def check_lne_archief(self):
        if len(self.ui.lneArchief.text()) > 0:
            self.ui.btnScan.setEnabled(True)

    def scan_for_dubbels(self):
        self.ui.btnSaveDb.setEnabled(False)
        self.ui.btnLoadDb.setEnabled(False)
        for i in range(self.ui.lstFiletype.count()):
            self.filetypes.append(self.ui.lstFiletype.item(i).text())
        items = []
        for x in range(self.ui.lstDirectories.count()):
            items.append(self.ui.lstDirectories.item(x).text())
        if not items:
            self.ui.txtInfo.append("Voeg een map toe aan de lijst!")
            return
        for folder in items:
            size = self.get_foldersize(folder)
            if size == 0:
                self.ui.txtInfo.append("De map " + folder + "is leeg!")
                return
            size = int(size/1048576)
            self.scan(folder, size)
        self.ui.txtInfo.append("Klaar met scannen")
        self.ui.btnSaveDb.setEnabled(True)
        self.ui.btnLoadDb.setEnabled(True)
            
                
    def get_foldersize(self, folder):
        total_size = os.path.getsize(folder)
        for item in os.listdir(folder):
            itempath = os.path.join(folder, item)
            if os.path.isfile(itempath):
                total_size += os.path.getsize(itempath)
            elif os.path.isdir(itempath):
                total_size += self.get_foldersize(itempath)
        return total_size

    def check_extension_valid(self,ext):
        if self.all:
            return True
        if ext in self.filetypes:
            return True
        return False

    def scan(self, mydir, sz):
        self.connection = sqlite3.connect(self.db)
        c = self.connection.cursor()
        self.ui.barExec.setMaximum(sz)
        self.ui.barDubbels.setMaximum(sz)
        total = 0
        dubbele_bestanden = 0
        wasted = 0
        archief = self.ui.lneArchief.text()
        if archief == None:
            QMessageBox.warning(self, 'Opgelet', "Vul de naam van de archiefmap in")
            return False
        vol = self.ui.lneVolume.text()
        if vol == None:
            QMessageBox.warning(self, 'Opgelet', "Vul de naam van het volume(schijf) in")
            return False
        for root, _, files in os.walk(mydir,topdown=True):            
            for file in files:
                try:
                    fl = str(file)
                    f = str(os.path.join(root, fl))                    
                    extension = os.path.splitext(f)[1]
                    valid = self.check_extension_valid(extension)
                    if valid:                   
                        fileSize = os.path.getsize(f)
                        total += fileSize
                        tot = int(total/1048576)
                        self.ui.barExec.setValue(tot)
                        fsum = self.hashfile(f)
                        curs = c.execute("SELECT * FROM uniekebestanden WHERE SUM = ?", (fsum,))
                        bestaat = curs.fetchone()
                        if bestaat is None:
                            self.ui.txtInfo.append(f)
                            self.ui.txtInfo.append("ok")
                        else:
                            dubbele_bestanden += 1
                            wasted += fileSize
                            wast = int(wasted/1048576)
                            self.ui.barDubbels.setValue(wast)
                            self.ui.txtDubbels.append(f)
                            self.dubbels.append(f)
                            continue
                        d = {'ID': self.primid, 'FILENAME': f, 'SIZE': fileSize,
                                'SUM': fsum, 'NAME': fl, 'EXT': extension, 'ARCHIEF': archief, 'VOLUME': vol}
                        c.execute("""INSERT INTO
                                uniekebestanden
                                (ID,FILENAME,SIZE,SUM,NAME,EXT,ARCHIEF,VOLUME)
                                VALUES (?,?,?,?,?,?,?,?);""",
                                tuple(d[k] for k in self.keylist))
                        self.connection.commit()
                        self.primid += 1
                except Exception as e:
                    self.ui.txtInfo.insertPlainText(str(e))
                    pass
        self.connection.close()
        if wasted != 0:
            megabyte = wasted/1048576
            mega = str(megabyte)
        else:
            mega = '0'        
        if dubbele_bestanden != 0:
            self.ui.btnRemoveDubbele.setEnabled(True)        
        self.ui.txtDubbels.append(str(dubbele_bestanden) + " aantal dubbele bestanden werden gevonden met een totale grootte van " + mega + " MB")                    


    def add_dir(self):
        folder = str(QFileDialog.getExistingDirectory(self, "Select Directory"))       
        self.ui.lstDirectories.addItem(folder)
        self.dirlist.append(folder)

    def remove_dir(self):
        selected = self.ui.lstDirectories.selectedItems()
        if not selected: return
        for item in selected:
            selectedfolder = item.text
            self.ui.lstDirectories.takeItem(self.ui.lstDirectories.row(item))
            self.dirlist.remove(selectedfolder)

    def deleteItem(self, lst, itemName):
        items_list = lst.findItems(itemName,QtCore.Qt.MatchExactly)
        for item in items_list:
            r = lst.row(item)
            lst.takeItem(r)

    def check_audio(self):
        if self.ui.checkAudio.isChecked():
            self.ui.lstFiletype.addItems(self.audio_ext)
        else:
            for ext in self.audio_ext:
                self.deleteItem(self.ui.lstFiletype, ext)

    def check_custom(self):
        if self.ui.checkCustom.isChecked():
            self.ui.lstFiletype.addItems(self.custom_ext)
        else:
            for ext in self.custom_ext:
                self.deleteItem(self.ui.lstFiletype, ext)


    def check_pictures(self):
        if self.ui.checkPic.isChecked():
            self.ui.lstFiletype.addItems(self.pic_ext)
        else:
            for ext in self.pic_ext:
                self.deleteItem(self.ui.lstFiletype, ext)


    def check_vids(self):
        if self.ui.checkVid.isChecked():
            self.ui.lstFiletype.addItems(self.vid_ext)
        else:
            for ext in self.vid_ext:
                self.deleteItem(self.ui.lstFiletype, ext)


    def check_docs(self):
        if self.ui.checkDoc.isChecked():
            self.ui.lstFiletype.addItems(self.document_ext)
        else:
            for ext in self.document_ext:                
                self.deleteItem(self.ui.lstFiletype, ext)

    def manage_custom_extensions(self):
        self.customdlg = CustomExtension(self)

    def remove_dubbels(self):        
        if self.dubbels:            
            for dubbel in self.dubbels:
                os.remove(dubbel)
            self.ui.txtInfo.append("De dubbele bestanden werden verwijderd")
        else:
            self.ui.txtInfo.append("De array met dubbele bestanden is leeg")
       
    # bereken md5sum van de bestandsinhoud
    def hashfile(self, path, blocksize=65536):
        afile = open(path, 'rb')
        hasher = hashlib.md5()
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
        afile.close()
        return hasher.hexdigest()


class CustomExtension(QDialog):
    
    def __init__(self, parent):
        super(CustomExtension, self).__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.customs = parent.custom_ext
        self.get_custom_extensions()
        self.ui.btnToevoegen.clicked.connect(self.voeg_extensie_toe)
        self.ui.buttonBox.accepted.connect(partial(self.geef_extensies_door,parent))
        self.show()

    def get_custom_extensions(self):
        if self.customs:
            self.ui.lstCustom.addItems(self.customs)

    def check_extensie(self,ext):
        if not ext.startswith("."):
            ext = "." + ext
        return ext

    def voeg_extensie_toe(self):
        extensie = self.ui.lneExtension.text()
        if not extensie:
            QMessageBox.warning(self, 'Opgelet', "Voeg een bestandstype extensie toe aan het invoegveld")
        else:
            extensie = self.check_extensie(extensie)
            self.ui.lstCustom.addItem(extensie)
            self.customs.append(extensie)
            self.write_customextensions(self.customs)

    def geef_extensies_door(self, parent):
        parent.custom_ext = self.customs


    def write_customextensions(self, extensions):
        with open('custom_extensions.csv', mode='w') as extensionsfile:
            extensionwriter = csv.writer(extensionsfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            extensionwriter.writerow(extensions)

        

  
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Dubbelzoeker()
    w.show()
    sys.exit(app.exec_())
