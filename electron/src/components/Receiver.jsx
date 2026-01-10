import FirmwareFlasherPanel from './FirmwareFlasherPanel';

function Receiver(props) {
  return (
    <FirmwareFlasherPanel
      title="Receiver"
      targetType="rx"
      showSerialX={true}
      allowWirelessBridge={false}
      {...props}
    />
  );
}

export default Receiver;
