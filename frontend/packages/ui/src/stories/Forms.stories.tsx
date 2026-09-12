import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";

import { Button } from "../components/Button";
import { FormActions, FormField, FormSection } from "../components/FormField";
import { Input, MoneyInput, NumberInput, Textarea } from "../components/Input";
import { LabelsInput, type Labels } from "../components/Misc";
import { Select } from "../components/Select";
import { Checkbox, RadioGroup, Switch } from "../components/Toggle";

const meta = { title: "Forms/Form pattern" } satisfies Meta;
export default meta;

export const RecordForm: StoryObj = {
  render: function Render() {
    const [labels, setLabels] = useState<Labels>({ fr: "Béton", en: "Concrete" });
    const [qty, setQty] = useState("12");
    const [price, setPrice] = useState("2500.00");
    const [unit, setUnit] = useState("SPECIMEN");
    const [billable, setBillable] = useState(true);
    const [mode, setMode] = useState("IMAGE");
    return (
      <form className="mx-auto flex max-w-2xl flex-col gap-6" onSubmit={(e) => e.preventDefault()}>
        <FormSection title="Identité" description="Le code est immuable, les libellés sont traduits.">
          <FormField label="Code" required help="Majuscules, chiffres, _ . -">
            <Input defaultValue="CONCRETE_COMPRESSION" />
          </FormField>
          <FormField label="Libellés" required>
            <LabelsInput value={labels} onChange={setLabels} />
          </FormField>
          <FormField label="Description" optionalLabel="optionnel">
            <Textarea placeholder="…" />
          </FormField>
        </FormSection>
        <FormSection title="Quantités et prix">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormField label="Quantité" error={Number(qty) <= 0 ? "Doit être positive" : undefined}>
              <NumberInput value={qty} onValueChange={setQty} decimals={0} unit="épr." />
            </FormField>
            <FormField label="Prix unitaire">
              <MoneyInput value={price} onValueChange={setPrice} currency="MRU" />
            </FormField>
            <FormField label="Unité">
              <Select value={unit} onValueChange={setUnit} options={[{ value: "SPECIMEN", label: "Éprouvette" }, { value: "VISIT", label: "Visite" }]} />
            </FormField>
          </div>
          <Checkbox checked={billable} onCheckedChange={setBillable} label="Facturable" />
          <Switch checked={billable} onCheckedChange={setBillable} label="Actif" />
          <RadioGroup value={mode} onValueChange={setMode} options={[{ value: "IMAGE", label: "Image de signature" }, { value: "DRAWN", label: "Dessinée sur l'appareil" }]} />
        </FormSection>
        <FormActions>
          <Button variant="outline">Annuler</Button>
          <Button variant="secondary">Enregistrer et nouveau</Button>
          <Button type="submit">Enregistrer</Button>
        </FormActions>
      </form>
    );
  },
};
