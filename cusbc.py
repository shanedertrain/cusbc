import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

FILEPATH_CUCBC = Path(__file__).parent / 'CUSBC.exe'

@dataclass
class HubInfo:
    """Data class to store information about a USB hub."""
    port: str
    num_ports: int
    firmware_version: str
    port_states: List[bool]  # List of port states represented as booleans

class PortState:
    """Helper class to manage port states in a more user-friendly way."""
    
    @staticmethod
    def from_bitmapped(bitmapped: str) -> tuple[bool]:
        """Convert reversed bitmapped port states (string) into a tuple of booleans."""
        return tuple([state == '1' for state in bitmapped[::-1]])
    
    @staticmethod
    def from_hex(hex_state: str) -> tuple[bool]:
        """Convert hex-encoded port states into a tuple of booleans (right to left)."""
        # Ensure the hex string is padded to an even length (e.g., 'F8' becomes 'F8')
        hex_state = hex_state.zfill(len(hex_state) + (len(hex_state) % 2))

        # Process each pair of hex characters (2 chars = 1 byte = 8 bits)
        port_states = []
        for i in range(0, len(hex_state), 2):
            # Get each byte (pair of hex chars)
            byte = hex_state[i:i+2]
            
            # Convert the byte to binary and reverse the bit order
            bin_state = bin(int(byte, 16))[2:].zfill(8)[::-1]
            
            # Add the reversed boolean values (1 -> True, 0 -> False)
            port_states.extend([bit == '1' for bit in bin_state])

        return tuple(port_states)

class CUSBC:
    """Class to interact with CUSBC.exe for USB hub control."""

    def __init__(self, port: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize with a specific COM port and optional password.
        
        :param port: The COM port of the USB hub (e.g., "COM1"). If None, the port is discovered automatically.
        :param password: Optional password for accessing certain features of the hub.
        """
        self.port = port
        self.password = password
        if not self.port:
            self.port = self.find_available_port()

    @staticmethod
    def _run_command(args: List[str]) -> str:
        """Run CUSBC.exe with the given arguments and return the output."""
        result = subprocess.run([FILEPATH_CUCBC] + args, capture_output=True, text=True)
        return result.stdout.strip()

    def find_available_port(self) -> str:
        """
        Find the first available USB hub port by querying all hubs.
        
        :return: The COM port of the first available USB hub.
        """
        hubs = self.query_hubs()
        if hubs:
            return hubs[0].port  # Return the first available hub's port
        else:
            raise ValueError("No available USB hub found.")

    def query_hubs(self) -> List[HubInfo]:
        """
        Query all connected USB hubs and return a list of HubInfo dataclasses.
        
        :return: A list of HubInfo dataclasses representing all connected hubs.
        """
        output = self._run_command(["/Q", "-F"])
        hub_count = int(output[:4])  # Extract hub count from the output
        ports = output[4:].split(",")  # Split the ports by commas
        
        hubs = []
        for port in ports:
            hub_info = self.query_hub_info(port)
            hubs.append(HubInfo(port=port, **hub_info))
        
        return hubs

    def query_hub_info(self, port: str) -> Dict[str, str]:
        """
        Query information about a specific USB hub based on the given port.
        
        :param port: The port identifier for the hub.
        :return: A dictionary with "port_states", "num_ports", and "firmware_version".
        """
        output = self._run_command([f"/Q:{port}", "-F"])
        num_ports = int(output[8:10], 16)
        return {
            "port_states": PortState.from_hex(output[:8])[:num_ports],  #4 bits per hex value
            "num_ports": num_ports,  # Extract the number of ports (in hex)
            "firmware_version": output[10:]  # Rest of the output is the firmware version
        }

    def get_port_states(self, mode: str = "-B") -> List[bool]:
        """
        Get the port states of the hub in either bit-mapped (-B) or hex (-H) format.
        
        :param mode: The format in which to return the port states, "-B" or "-H".
        :return: The port states as a list of booleans.
        """
        raw_state = self._run_command([f"/G:{self.port}", mode])
        if mode == "-B":
            return PortState.from_bitmapped(raw_state)
        elif mode == "-H":
            return PortState.from_hex(raw_state)
        else:
            raise ValueError("Invalid mode: choose '-B' for bit-mapped or '-H' for hex.")

    def set_port_states(self, state: tuple[bool, bool, bool, bool], mode: str = "B") -> None:
        """
        Set the port states of the hub using a tuple of booleans for the state.

        :param state: The state to set the ports to as a tuple of booleans.
        :param mode: The format for the state, "B" for bit-mapped or "H" for hex.
        """
        # Reverse the state before processing
        state = state[::-1]

        if mode == "B":
            # Convert the reversed state to a bit-mapped string
            state_str = ''.join(['1' if s else '0' for s in state])
        elif mode == "H":
            # Convert the reversed state to a hex string
            state_str = hex(int(''.join(['1' if s else '0' for s in state]), 2))[2:]
        else:
            raise ValueError("Invalid mode: choose 'B' for bit-mapped or 'H' for hex.")
        
        args = [f"/S:{self.port}"]
        if self.password:
            args.append(self.password)
        args.append(f"{mode}:{state_str}")
        
        # Run the command with the constructed arguments
        self._run_command(args)

    def save_initial_states(self) -> None:
        """Save the current port states to flash memory as the initial states."""
        if not self.password:
            raise ValueError("Password is required for this operation.")
        self._run_command([f"/W:{self.port}", self.password])

    def restore_factory_defaults(self) -> None:
        """Restore the hub to its factory default settings."""
        if not self.password:
            raise ValueError("Password is required for this operation.")
        self._run_command([f"/D:{self.port}", self.password])

    def reset_hub(self) -> None:
        """Reset the entire USB hub."""
        if not self.password:
            raise ValueError("Password is required for this operation.")
        self._run_command([f"/R:{self.port}", self.password])

    def change_password(self, new_password: str) -> None:
        """Change the password for the hub."""
        if not self.password:
            raise ValueError("Current password is required.")
        self._run_command([f"/P:{self.port}", self.password, new_password])
        self.password = new_password

if __name__ == "__main__":
    hub = CUSBC(password="pass")  # Let the port be discovered automatically

    # Query all hubs connected to the computer
    hubs = hub.query_hubs()
    for hub_info in hubs:
        print(f"Hub: {hub_info.port}, Num Ports: {hub_info.num_ports}, Firmware Version: {hub_info.firmware_version}")

    # Get information about the specific hub
    hub_info = hub.query_hubs()
    print(f"Hub info: {hub_info}")

    # Get port states in bit-mapped format
    port_states = hub.get_port_states()
    print(f"Port states (bit-mapped): {port_states}")

    # Change port states (example)
    hub.set_port_states(state=(False, False, True, False), mode="B")

    # Get port states in bit-mapped format
    port_states = hub.get_port_states()
    print(f"Port states (bit-mapped): {port_states}")

    # # Save current port states as initial states
    # hub.save_initial_states()

    # # Restore hub to factory defaults
    # hub.restore_factory_defaults()

    # # Reset the hub
    # hub.reset_hub()

    # # Change the password for the hub
    # hub.change_password(new_password="newpass")
