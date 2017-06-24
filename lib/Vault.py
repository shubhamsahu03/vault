
import getpass, json, base64, time

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
import pyperclip

class Vault:

    config = None # Will hold user configuration
    vaultPath = None # Vault file location
    vault = None # Vault content once decrypted
    timer = None # Set a timer to autolock the vault

    def __init__(self, config, vaultPath):
        self.config = config;
        self.vaultPath = vaultPath;

    def setup(self):
        """
            Master key setup
        """

        global masterKey

        print('Welcome to Vault. Please choose a secure secret key.');
        print()
        masterKey = getpass.getpass('Please choose a master key:');
        masterKeyRepeat = getpass.getpass('Please confirm your master key:');

        if len(masterKey) < 8:
            print()
            print('The master key should be at least 8 characters. Please try again!');
            print()
            # Try again
            self.setup();
        elif masterKey == masterKeyRepeat:
            # Create empty vault
            self.vault = {}
            self.saveVault()
            print()
            print("Your vault has been created and encrypted with your master key.")
            print("Your unique salt is: %s " % (self.config['salt']))
            print("Write it down. If you lose your config file you will need it to unlock your vault.")
            print()
            self.unlock()
        else:
            print()
            print('The master key does not match its confirmation. Please try again!');
            print()
            # Try again
            self.setup();

    def unlock(self, showMenu = True, tentative = 1):
        """
            Asking the user for his master key and trying to unlock the vault
        """

        global masterKey

        # Get master key
        masterKey = getpass.getpass('Please enter your master key:');

        try:
            self.openVault() # Unlock vault
        except Exception as e:
            if tentative >= 3:
                import sys

                # Stop trying after 3 attempts
                print('Vault cannot be opened.');
                print()
                sys.exit()
            else:
                # Try again
                print('Master key is incorrect. Please try again!');
                print()
                self.unlock(showMenu, tentative + 1)

        if showMenu:
            # Show secret count
            self.showSecretCount()

            # Print vault content (for debug purpose)
            #print(json.dumps(self.vault, sort_keys=True, indent=4, separators=(',', ': ')))

            self.menu()

    def saveVault(self):
        """
            Save vault
        """

        cipher = AES.new(self.getHash(masterKey), AES.MODE_EAX)
        data = str.encode(json.dumps(self.vault));
        ciphertext, tag = cipher.encrypt_and_digest(data)

        f = open(self.vaultPath, "wb")
        try:
            [ f.write(x) for x in (cipher.nonce, tag, ciphertext) ]
        finally:
            f.close()

    def openVault(self):
        """"
            Open the vault with the master key
        """

        f = open(self.vaultPath, "rb")
        try:
            nonce, tag, ciphertext = [ f.read(x) for x in (16, 16, -1) ]
        finally:
            f.close()

        # Unlock valt with key
        cipher = AES.new(self.getHash(masterKey), AES.MODE_EAX, nonce)
        data = cipher.decrypt_and_verify(ciphertext, tag)

        # Set vault content to class level var
        self.vault = json.loads(data.decode("utf-8") )

    def getHash(self, masterKey):
        """
            Returns a 32 bytes hash for a given master key
        """

        h = SHA256.new()
        for i in range(1, 10000):
            h.update(str.encode(str(i) + self.config['salt'] + masterKey))
        return base64.b64decode(str.encode(h.hexdigest()[:32]))

    def addItemInput(self):
        """
            Add a new secret based on user input
        """

        # Show categories
        print()
        print ("* Available categories:")
        self.categoriesList()
        print()

        # Category ID
        categoryId = input('* Choose a category number (or leave empty for none): ')
        if categoryId != '':
            if not self.categoryCheckId(categoryId):
                print('Invalid category. Please try again.')
                self.addItemInput()

        # Basic settings
        name = input('* Name / URL: ')
        login = input('* Login: ')
        password = getpass.getpass('* Password: ');

        # Notes
        print('* Notes: (press [ENTER] twice to complete)')
        notes = []
        while True:
            input_str = input("> ")
            if input_str == "":
                break
            else:
                notes.append(input_str)

        # Save item
        self.addItem(categoryId, name, login, password, "\n".join(notes))

        # Confirmation
        print()
        print('The new item has been saved to your vault.')
        print()
        self.menu()

    def addItem(self, categoryId, name, login, password, notes):
        """
            Add a new secret to the vault
        """

        # Create `secret` item if necessary
        if not self.vault.get('secret'):
            self.vault['secrets'] = []

        # Add item to vault
        self.vault['secrets'].append({
            'category': categoryId,
            'name': name,
            'login': login,
            'password': password,
            'notes': notes
        });

        self.saveVault()

    def menu(self):
        """
            Display user menu
        """

        # Set auto lock timer
        self.setAutoLockTimer()

        print()
        command = input('Choose a command [(g)et / (s)earch / show (all) / (a)dd / (d)elete / (cat)egories / (l)ock / (q)uit]: ')

        # Check auto lock timer
        if command != 'l' and command != 'q': # Except if the user wants to lock the vault or quit the application
            self.checkAutoLockTimer()

        # Action based on command
        if command == 'g': # Get an item
             self.get()
        elif command == 's': # Search an item
             self.search()
        elif command == 'all': # Show all items
             self.all()
        elif command == 'a': # Add an item
             self.addItemInput()
        elif command == 'd': # Delete an item
             self.delete()
        elif command == 'cat': # Manage categories
             self.categoriesMenu()
        elif command == 'l': # Lock the vault and ask for the master key
             self.lock()
        elif command == 'q': # Lock the vault and quit
             self.quit()
        else: # Back to menu
            self.menu()

    def get(self):
        """
            Quickly retrieve an item from the vault with its ID
        """

        from lib.Misc import confirm

        print()
        id = input('Enter item number: ')

        try:
            # Get item
            item = self.vault['secrets'][int(id)]

            # Show item
            print ('* Category: %s' % (self.categoryName(item['category'])))
            print ('* Name / URL: %s' % (item['name']))
            print ('* Login: %s' % (item['login']))
            print ('* Notes: %s' % (item['notes']))
            print()
            if confirm('Copy password to clipboard instead of displaying it?', True):
                # Copy to clipboard
                self.clipboard(item['password'])
                print ('* The password has been copied to the clipboard.')
                self.waitAndEraseClipboard()
            else:
                print ('* Password: %s' % (item['password']))
        except Exception as e:
            print('Item does not exist.');

        self.menu()

    def search(self):
        """
            Search items
        """

        print()
        search = input('Enter search: ')

        if self.vault.get('secret'):
            # Iterate thru the items
            results = []
            for i, item in enumerate(self.vault['secrets']):
                # Search in name, login and notes
                if search.upper() in item['name'].upper() or search.upper() in item['login'].upper() or search.upper() in item['notes'].upper():
                    # Add item to search results
                    results.append([
                        i,
                        self.categoryName(item['category']),
                        item['name'],
                        item['login']
                    ]);

            # If we have search results
            if len(results) > 0:
                # Show results table
                from tabulate import tabulate
                print()
                print (tabulate(results, headers=['Item', 'Category', 'Name / URL', 'Login']))
            else:
                print('No results!')
        else:
            print("There are no secrets saved yet.")

        self.menu()

    def all(self):
        """
            Show all items in a table
        """

        if self.vault.get('secret'):
            # Iterate thru the items
            results = []
            for i, item in enumerate(self.vault['secrets']):
                # Add item to results
                results.append([
                    i,
                    self.categoryName(item['category']),
                    item['name'],
                    item['login']
                ]);

            # Show results table
            from tabulate import tabulate
            print()
            print (tabulate(results, headers=['Item', 'Category', 'Name / URL', 'Login']))
        else:
            print("There are no secrets saved yet.");

        self.menu()

    def delete(self):
        """
            Quickly delete an item from the vault with its ID
        """

        from lib.Misc import confirm

        print()
        id = input('Enter item number: ')

        try:
            # Get item
            item = self.vault['secrets'][int(id)]

            # Show item
            print ('* Name / URL: %s' % (item['name']))
            print ('* Login: %s' % (item['login']))
            print()
            if confirm('Confirm deletion?', False):
                # Remove item
                self.vault['secrets'].pop(int(id))

                # Save the vault
                self.saveVault()
        except Exception as e:
            print('Item does not exist.');

        self.menu()

    def setAutoLockTimer(self):
        """
            Set auto lock timer
        """

        self.timer = int(time.time())

    def checkAutoLockTimer(self):
        """
            Check auto lock timer and lock the vault if necessary
        """

        if int(time.time()) > self.timer + int(self.config['autoLockTTL']):
            print()
            print("The vault has been locked due to inactivity.")
            print()
            self.lock()

    def lock(self):
        """
            Lock the vault and ask the user to login again
        """

        # Lock the vault
        self.vault = None

        # Unlock form
        self.unlock()

    def quit(self):
        """
            Lock the vault and exit the program
        """

        import sys

        # Lock the vault
        self.vault = None

        # Exit program
        sys.exit()

    def showSecretCount(self):
        """
            If the vault has secrets, this method will show the total number of secrets.
        """

        if self.vault.get('secret'):
            count = len(self.vault['secrets'])

            print()
            if count > 1:
                print("%s items are saved in the vault" % (count))
            else:
                print("%s item is saved in the vault" % (count))

    def categoriesMenu(self):
        """
            Categories menu
        """

        # List categories
        self.categoriesList()

        print()
        command = input('Choose a command [(a)dd a category / (r)rename a category / (d)elete a category / (b)back to Vault]: ')

        # Action based on command
        if command == 'a': # Add a category
             self.categoryAdd()
        elif command == 'r': # Rename a category
             self.categoryRename()
        elif command == 'd': # Delete a category
             self.categoryDelete()
        elif command == 'b': # Back to vault menu
             self.menu()
        else: # Back to menu
            self.categoriesMenu()

    def categoriesList(self):
        """
            List all categories
        """

        if self.vault.get('categories'):
            # Iterate thru the items
            results = []
            for i, item in enumerate(self.vault['categories']):
                # Add item to results
                if item['active'] == True:
                    results.append([
                        i,
                        item['name']
                    ]);

            # If we have active categories
            if len(results) > 0:
                # Show results table
                from tabulate import tabulate
                print()
                print (tabulate(results, headers=['Item', 'Category name']))
            else:
                print('There are no categories yet.')
        else:
            print()
            print("There are no categories yet.");

    def categoryAdd(self):
        """
            Create a new category
        """

        # Basic input
        name = input('Category name: ')

        # Create `categories` item if necessary
        if not self.vault.get('categories'):
            self.vault['categories'] = []

        # Add new category to vault
        self.vault['categories'].append({
            'name': name,
            'active': True
        });

        self.saveVault()

        # Confirmation
        print()
        print('The category has been created.')

        self.categoriesMenu()

    def categoryDelete(self):
        """
            Quickly delete a category from the vault with its ID
        """

        from lib.Misc import confirm

        print()
        id = input('Enter category number: ')

        try:
            # Get item
            item = self.vault['categories'][int(id)]

            # Show item
            print ('* Category: %s' % (item['name']))
            print()
            if self.categoryIsUsed(id) == False:
                if confirm('Confirm deletion?', False):
                    if self.categoryIsUsed(id) == False:
                        # Deactivate item
                        self.vault['categories'][int(id)]['active'] = False

                        # Save the vault
                        self.saveVault()

                        print('The category has been deleted.');
            else:
                print('The category cannot be deleted because it is currently used by some secrets.');
        except Exception as e:
            print('Category does not exist.');

        self.categoriesMenu()

    def categoryIsUsed(self, categoryId):
        """
            Will return `True` if a category is currently used by a secret
        """

        if self.vault.get('secret'):
            # Iterate thru the items
            for item in self.vault['secrets']:
                if categoryId and item['category'] == categoryId: # If the item has a category and it is the category searched
                    return True
        else:
            return False

        return False

    def categoryRename(self):
        """
            Quickly rename a category from the vault with its ID
        """

        from lib.Misc import confirm

        print()
        id = input('Enter category number: ')

        try:
            # Get item
            item = self.vault['categories'][int(id)]

            # Show item
            print ('* Category: %s' % (item['name']))

            # Basic input
            name = input('* New category name: ')

            # Deactivate item
            self.vault['categories'][int(id)]['name'] = name

            # Save the vault
            self.saveVault()

            print('The category has been renamed.');
        except Exception as e:
            print('Category does not exist.');

        self.categoriesMenu()

    def categoryCheckId(self, categoryId):
        """
            When adding a secret, check if a category ID is valid
        """

        try:
            # Get item
            item = self.vault['categories'][int(categoryId)]

            if item['active'] == True: # Return `true` if the category is active
                return True
        except Exception as e:
            return False

        # Default
        return False

    def categoryName(self, categoryId):
        """
            Returns a category name
        """

        try:
            # Get item
            item = self.vault['categories'][int(categoryId)]

            if item['active'] == True: # Return category name if the category is active
                return item['name']
        except Exception as e:
            return 'n/a'

        # Default
        return 'n/a'

    def clipboard(self, toCopy):
        """
            Copy an item to the clipboard
        """

        pyperclip.copy(toCopy)

    def waitAndEraseClipboard(self):
        """
            Wait X seconds and erase the clipboard
        """

        print("* Clipboard will be erased in %s seconds" % (self.config['clipboardTTL']))
        for i in range(0, int(self.config['clipboardTTL'])):
            print('.', end='', flush=True)
            time.sleep(1) # Sleep 1 sec
        print();
        self.clipboard('') # Empty clipboard

    def changeKey(self):
        """
            Replace vault key
            Will ask user to initially unlock the vault
            Then the user will input a new master key and the vault will be saved with the new key
        """

        global masterKey

        # Unlock the vault with the existing key
        if self.vault is None: # Except if it's already unlocked
            self.unlock(False) # `False` = don't load menu after unlocking

        # Choose a new key
        print()
        newMasterKey = getpass.getpass('Please choose a new master key:');
        newMasterKeyRepeat = getpass.getpass('Please confirm your new master key:');

        if len(newMasterKey) < 8:
            print()
            print('The master key should be at least 8 characters. Please try again!');
            print()
            # Try again
            self.changeKey();
        elif newMasterKey == newMasterKeyRepeat:
            # Override master key
            masterKey = newMasterKey

            # Save vault with new master key
            self.saveVault()

            print()
            print("Your master key has been updated.")
            print()
            self.unlock()
        else:
            print()
            print('The master key does not match its confirmation. Please try again!');
            print()
            # Try again
            self.changeKey();
