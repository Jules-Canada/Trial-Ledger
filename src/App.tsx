import sotorasib from "../data/drugs/sotorasib.json";
import type { Drug } from "./types";
import { SignalLedger } from "./components/SignalLedger";

const drug = sotorasib as unknown as Drug;

export default function App() {
  return (
    <div className="ledger-frame">
      <SignalLedger drug={drug} />
    </div>
  );
}
