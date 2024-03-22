import datetime
import sqlite3
import tkinter as tk
from PIL import ImageGrab, ImageTk, Image
import pyautogui
import easyocr
import cv2
import numpy as np
import matplotlib.pyplot as plt

# Return the digit to total character ratio of a string
def dt_ratio(text=""):
    d = sum(1 for char in text if char.isdigit())
    t = len(text)
    return d / t if t else 0

# Try our best to handle the output from easyocr to get the item name and item price
def datahandler(text=""):
    item_name = ""
    item_price = ""

    # Fix common spelling mistakes of numbers
    def l2d(text=""):
        replacements = {"o": "0", "O": "0", "s": "5", "S": "5", "G": "6", ",": ""}
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    # Try to divide the easyocr input into two, name and price
    for line in text.splitlines():
        # Last line is always the price
        if line == text.splitlines()[-1]:
            # Fix spellings
            line = l2d(line)
            # Easyocr usually cant recognize the 1s if it is the first digit
            # We assume there's a 1 at the front, if the rest of the digits are 0s
            try:
                if int(line) == 0:
                    line = "1" + line[0:]
            except ValueError:
                line = 0
            item_price = line

        else:
            # If the string is 50% digits, or it has a "," in it, it is considered to be the price.
            if dt_ratio(line) >= 0.5 or line.count(",") > 1:
                line = l2d(line)
                item_price = line
            # Otherwise we assume it is a part of the item name.
            else:
                # Fix the spelling of l which was mistaken for a 1
                # This can be improved.
                line = line.replace("1", "l")
                item_name += line + " "

    # Remove the excess space at the end of the item name.
    if item_name.endswith(" "):
        item_name = item_name[:-1]

    return item_name, item_price


class GUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("NosTale Market Helper")

        # Database
        self.conn = sqlite3.connect("item_prices.db")
        self.cursor = self.conn.cursor()
        self.create_table()

        # Placing the GUI components
        self.label = tk.Label(self, text="Press the 'Capture Coordinates' button, hover over the top left of the "
                                         "listing, press any key.")
        self.label.pack()

        self.coordinates_button = tk.Button(self, text="Capture Coordinates", command=self.get_coordinates)
        self.coordinates_button.pack()

        self.coordinates_label = tk.Label(self, text="")
        self.coordinates_label.pack()

        self.screenshot_button = tk.Button(self, text="Capture Screenshot", command=self.capture_screenshot)
        self.screenshot_button.pack()

        self.screenshot_label = tk.Label(self)
        self.screenshot_label.pack()

        self.filter_frame = tk.Frame(self)
        self.filter_frame.pack(pady=10)

        self.filter_entry = tk.Entry(self.filter_frame)
        self.filter_entry.pack(side=tk.LEFT, padx=5)

        self.filter_button = tk.Button(self.filter_frame, text="Filter", command=self.filter_data)
        self.filter_button.pack(side=tk.LEFT, padx=5)

        self.price_change_button = tk.Button(self.filter_frame, text="Show Price Change", command=self.show_price_change)
        self.price_change_button.pack(side=tk.LEFT, padx=5)

        self.add_item_frame = tk.Frame(self)
        self.add_item_frame.pack(pady=10)

        tk.Label(self.add_item_frame, text="Item Name:").grid(row=0, column=0, padx=5)
        self.item_name_entry = tk.Entry(self.add_item_frame)
        self.item_name_entry.grid(row=0, column=1, padx=5)

        tk.Label(self.add_item_frame, text="Item Price:").grid(row=1, column=0, padx=5)
        self.item_price_entry = tk.Entry(self.add_item_frame)
        self.item_price_entry.grid(row=1, column=1, padx=5)

        tk.Label(self.add_item_frame, text="Date:").grid(row=2, column=0, padx=5)
        self.date_entry = tk.Entry(self.add_item_frame)
        self.date_entry.grid(row=2, column=1, padx=5)

        self.add_button = tk.Button(self.add_item_frame, text="Add Item", command=self.add_item)
        self.add_button.grid(row=3, columnspan=2, pady=5)

        self.delete_button = tk.Button(self, text="Delete Selected", command=self.delete_selected)
        self.delete_button.pack(pady=10)

        self.listbox_frame = tk.Frame(self)
        self.listbox_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        self.listbox_scroll = tk.Scrollbar(self.listbox_frame, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(self.listbox_frame, yscrollcommand=self.listbox_scroll.set)
        self.listbox_scroll.config(command=self.listbox.yview)
        self.listbox_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(fill=tk.BOTH, expand=True)

        # Initialize EasyOCR with English
        # English: en
        # Turkish: tr
        self.reader = easyocr.Reader(['en'])

        self.load_listbox_data()

    # Create a table to store the data
    def create_table(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS items (
                                id INTEGER PRIMARY KEY,
                                item_name TEXT NOT NULL,
                                item_price INTEGER NOT NULL,
                                date DATE NOT NULL
                            )''')
        self.conn.commit()

    # Filter the db with the textbox input
    def filter_data(self):
        # Clear the listbox first, there is no set method, so we have to clear and add
        self.listbox.delete(0, tk.END)
        filter_text = self.filter_entry.get()
        self.cursor.execute("SELECT * FROM items WHERE item_name LIKE ?", ('%' + filter_text + '%',))
        filtered_items = self.cursor.fetchall()
        # Add the filtered items to the listbox
        for item in filtered_items:
            self.listbox.insert(tk.END, f"{item[0]}\t{item[1]} - {item[2]} - {item[3]}")

    # Add item to the db
    def add_item(self):
        # Get the data from the related textboxes
        item_name = self.item_name_entry.get()
        item_price = float(self.item_price_entry.get())
        date = self.date_entry.get()
        try:
            self.cursor.execute("INSERT INTO items (item_name, item_price, date) VALUES (?, ?, ?)", (item_name, item_price, date))
            self.conn.commit()
        except Exception as e:
            print("error")

        self.load_listbox_data()

    # Delete the selected entry from the db
    def delete_selected(self):
        selected_index = self.listbox.curselection()
        if selected_index:
            item_id = str(self.listbox.get(selected_index)).split("\t")[0]

            self.cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
            self.conn.commit()
            self.filter_data()

    # Load the whole db into the listbox
    # I used the filter method as a backbone, which is not optimal :P
    # This one can be improved.
    def load_listbox_data(self):
        self.listbox.delete(0, tk.END)
        self.cursor.execute("SELECT * FROM items WHERE item_name LIKE ?", '%')
        filtered_items = self.cursor.fetchall()
        for item in filtered_items:
            self.listbox.insert(tk.END,
                                f"{item[0]}\t{item[1]} - {item[2]} - {item[3]}")  # Display filtered data in the listbox

    # This is to plot the price change of the filtered items throughout time.
    # It does not work as intended at all.
    # It sometimes uses scientific notation
    # It doesn't plot the x-axis relative to the date
    # It shows extra items if their name is in the desired item's name. Such as "apple" and "apple pie".
    def show_price_change(self):
        filter_text = self.filter_entry.get()

        self.cursor.execute("SELECT * FROM items WHERE item_name LIKE ?", ('%' + filter_text + '%',))
        filtered_items = self.cursor.fetchall()

        item_names = []
        item_prices = []
        item_dates = []
        for item in filtered_items:
            item_names.append(item[1])
            item_prices.append(item[2])
            item_dates.append(datetime.datetime.strptime(item[3], "%d-%m-%Y %H:%M"))

        # Sort the data by date
        # This is actually unnecessary as the date value is picked at the moment of capturing the screenshot
        # and time only moves forward (sadly)
        # But for handwritten date values, it fixes the plot.
        sorted_indices = sorted(range(len(item_dates)), key=lambda k: item_dates[k])
        item_prices = [item_prices[i] for i in sorted_indices]
        item_dates = [item_dates[i] for i in sorted_indices]

        # Plot the data
        plt.figure(figsize=(10, 6))
        plt.plot(item_dates, item_prices, marker='o', linestyle='-')
        plt.title(filter_text + ' Price Change Over Time')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    def get_coordinates(self):
        self.coordinates_label.config(text="Hover over the top left of the listing and press any key.")

        # Wait for a key press to get the coordinates
        self.bind("<KeyPress>", lambda event: self.update_coordinates())

    def update_coordinates(self):
        x, y = pyautogui.position()
        self.coordinates_label.config(text=f"Coordinates: {x}, {y}")
        self.unbind("<KeyPress>")
        self.coordinates = (x, y)

    def capture_screenshot(self):

        x, y = self.coordinates
        screenshot = pyautogui.screenshot()
        # This values work just fine
        item_image = screenshot.crop((x, y, x + 350, y + 50))

        item_image = cv2.cvtColor(np.array(item_image), cv2.COLOR_RGB2BGR)

        # We apply some filters to get better results with easyocr
        gray = cv2.cvtColor(item_image, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY_INV)[1]

        # Use easyocr to read the processed image
        item_details = self.reader.readtext(thresh)

        text = ''
        for result in item_details:
            text += result[1] + '\n'

        # Display the screenshot for the user to see the captured area, so they can change the coordinates if there's
        # a problem.
        item_image = Image.fromarray(cv2.cvtColor(thresh, cv2.COLOR_BGR2RGB))
        screenshot_tk = ImageTk.PhotoImage(item_image)
        self.screenshot_label.config(image=screenshot_tk)
        self.screenshot_label.image = screenshot_tk

        self.item_name_entry.delete(0, tk.END)
        self.item_price_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)

        # Instead of adding them straight to the db, we pass the data into textboxes
        # so the user can fix the mistakes.
        self.item_name_entry.insert(0, datahandler(text)[0])
        self.item_price_entry.insert(0, datahandler(text)[1])
        self.date_entry.insert(0, (datetime.datetime.now().strftime("%d-%m-%Y %H:%M")))


if __name__ == "__main__":
    app = GUI()
    app.mainloop()
