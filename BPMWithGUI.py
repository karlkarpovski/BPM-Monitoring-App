import asyncio
import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
from bleak import BleakScanner, BleakClient
import threading
import os

HEART_RATE_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

class HeartRateMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("💓 Heart Rate Monitor")

        # Main menu frame
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(padx=10, pady=10)

        self.scan_button = tk.Button(self.main_frame, text="Scan for Heartbeat Devices", command=self.scan_devices)
        self.scan_button.pack(pady=10)

        self.device_listbox = tk.Listbox(self.main_frame, height=6, width=40)
        self.device_listbox.pack(pady=10)

        self.connect_button = tk.Button(self.main_frame, text="Connect to Device", command=self.connect_device)
        self.connect_button.pack(pady=10)

        # Heart rate display will be in a separate frame
        self.heart_rate_frame = None
        self.device_address = None

        # For managing the asyncio event loop
        self.loop = None

    def scan_devices(self):
        """Scans for available BLE devices and displays them in the listbox."""
        self.device_listbox.delete(0, tk.END)
        self.device_listbox.insert(tk.END, "Scanning...")
        self.start_ble_thread(self._scan_devices)

    def start_ble_thread(self, target):
        """Starts the BLE task in a new thread."""
        ble_thread = threading.Thread(target=target)
        ble_thread.start()

    def _scan_devices(self):
        """Asynchronous scanning for available BLE heart rate devices."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        devices = loop.run_until_complete(BleakScanner.discover())
        
        if not devices:
            messagebox.showerror("Error", "No devices found. Ensure your BLE device is in pairing mode.")
            return

        self.device_listbox.delete(0, tk.END)
        for device in devices:
            self.device_listbox.insert(tk.END, f"{device.name or 'Unknown'} - {device.address}")
        
    def connect_device(self):
        """Connects to the selected device from the listbox."""
        try:
            selection = self.device_listbox.curselection()
            if not selection:
                messagebox.showerror("Error", "Please select a device.")
                return

            self.device_address = self.device_listbox.get(selection[0]).split(" - ")[-1]
            self.device_listbox.delete(0, tk.END)
            self.device_listbox.insert(tk.END, f"Connecting to {self.device_address}...")

            # Hide the scanning UI once a device is selected
            self.scan_button.pack_forget()
            self.device_listbox.pack_forget()
            self.connect_button.pack_forget()

            self.start_heart_rate_gui()

            # Start BLE loop for connection and heart rate monitoring
            self.start_ble_thread(self._connect_and_monitor)

        except Exception as e:
            messagebox.showerror("Connection Error", f"An error occurred: {e}")

    def start_heart_rate_gui(self):
        """Sets up the heart rate monitoring interface in the GUI."""
        if self.heart_rate_frame:
            self.heart_rate_frame.destroy()

        self.heart_rate_frame = tk.Frame(self.root)
        self.heart_rate_frame.pack(padx=10, pady=10)

        self.heartRateLabel = tk.Label(self.heart_rate_frame, text="Heart Rate: -- BPM", font=("Arial", 20))
        self.heartRateLabel.pack(pady=10)

        # Graph setup
        self.fig, self.ax = plt.subplots(figsize=(7, 4))
        self.ax.set_title("Heart Rate Data")
        self.ax.set_ylim(50, 100)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("BPM")
        self.HeartRateValues = deque([0]*50, maxlen=50)

        # Embed Matplotlib in Tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.heart_rate_frame)
        self.canvas.get_tk_widget().pack()

    def _connect_and_monitor(self):
        """Connects to the BLE device and monitors the heart rate."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def connect_and_monitor():
            try:
                async with BleakClient(self.device_address) as client:
                    if await client.is_connected():
                        print(f"✅ Connected to {self.device_address}\n")
                        print("💓 Heart rate updates will appear in the GUI and terminal.")

                        # Read heart rate data
                        def heart_rate_callback(sender, data):
                            heart_rate = data[1]  # Second byte contains the heart rate value
                            print(f"💓 Heart rate: {heart_rate} BPM")
                            self.update_heart_rate(heart_rate)

                        await client.start_notify(HEART_RATE_UUID, heart_rate_callback)

                        while True:
                            await asyncio.sleep(1)  # Keep the loop running

            except Exception as e:
                print(f"⚠️ Error: {e}")
                # Retry connection after a delay if needed
                await asyncio.sleep(5)
                await connect_and_monitor()

        loop.run_until_complete(connect_and_monitor())

    def update_heart_rate(self, bpm):
        """Updates the heart rate label and graph dynamically."""
        self.heartRateLabel.config(text=f"Heart Rate: {bpm} BPM")
        self.HeartRateValues.append(bpm)

        # Get current y-axis limits
        y_min, y_max = self.ax.get_ylim()

        # Expand Y-axis ONLY if BPM exceeds current max
        if bpm + 5 > y_max:
            y_max = bpm + 5
        if bpm - 5 < y_min:
            y_min = bpm - 5

        # Update the graph
        self.ax.clear()
        self.ax.set_title("Heart Rate Data")
        self.ax.set_ylim(y_min, y_max)  # Expand Y-axis dynamically
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("BPM")
        self.ax.plot(self.HeartRateValues, marker="", linestyle="-", color="red")
        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = HeartRateMonitorApp(root)
    root.mainloop()
