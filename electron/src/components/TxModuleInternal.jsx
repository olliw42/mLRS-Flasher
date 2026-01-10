import FirmwareFlasherPanel from './FirmwareFlasherPanel';

function TxModuleInternal(props) {
  return (
    <FirmwareFlasherPanel
      title="Tx Module (Internal)"
      targetType="txint"
      showSerialX={false}
      allowWirelessBridge={true}
      {...props}
    />
  );
}

export default TxModuleInternal;
