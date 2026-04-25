import { type Component, createSignal, Show } from "solid-js";
import { createForm, setValue, type PartialValues } from "@modular-forms/solid";
import {
  Eye,
  EyeOff,
  ChevronRight,
  Wallet,
  SlidersHorizontal,
} from "lucide-solid";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { Select } from "~/components/ui/select";
import { Checkbox } from "~/components/ui/checkbox";
import { TagInput } from "~/components/ui/tag-input";
import { Panel, PanelHeader, PanelBody } from "~/components/ui/panel";
import { SectionLabel } from "~/components/ui/section-label";
import { ToggleGroup } from "~/components/ui/toggle-group";
import { Textarea } from "~/components/ui/textarea";
import { cn } from "~/lib/utils";
import {
  createTraderFormSchema,
  editTraderFormSchema,
  type CreateTraderForm,
} from "~/lib/schemas/trader-config";

export interface TraderConfigFormProps {
  initialValues?: Partial<CreateTraderForm>;
  onSubmit: (data: CreateTraderForm) => Promise<void>;
  isSubmitting?: boolean;
  submitLabel?: string;
  isEditing?: boolean;
}

export const TraderConfigForm: Component<TraderConfigFormProps> = (props) => {
  const [error, setError] = createSignal<string | null>(null);
  const [showPrivateKey, setShowPrivateKey] = createSignal(false);
  const [bucketMode, setBucketMode] = createSignal<"manual" | "auto">("auto");
  const [advancedOpen, setAdvancedOpen] = createSignal(false);
  const [maxLeverageEnabled, setMaxLeverageEnabled] = createSignal(
    (props.initialValues?.config?.trader_settings?.trading_strategy?.risk_parameters?.max_leverage ?? null) !== null
  );

  // Use edit schema when editing (no wallet_address/private_key validation)
  const isEditing = props.isEditing ?? false;

  // Custom validator that skips wallet_address/private_key validation when editing
  const validateForm = (values: PartialValues<CreateTraderForm>) => {
    if (isEditing) {
      const result = editTraderFormSchema.safeParse(values);
      if (!result.success) {
        const errors: Record<string, string> = {};
        result.error.errors.forEach((err) => {
          errors[err.path.join(".")] = err.message;
        });
        return errors;
      }
      return {};
    } else {
      const result = createTraderFormSchema.safeParse(values);
      if (!result.success) {
        const errors: Record<string, string> = {};
        result.error.errors.forEach((err) => {
          errors[err.path.join(".")] = err.message;
        });
        return errors;
      }
      return {};
    }
  };

  const [form, { Form: FormComponent, Field: FormField }] =
    createForm<CreateTraderForm>({
      validate: validateForm,
      initialValues: props.initialValues ?? {
        wallet_address: "",
        private_key: "",
        name: "",
        description: "",
        config: {
          provider_settings: {
            exchange: "hyperliquid",
            network: "mainnet",
            self_account: { address: "", is_sub: false },
            copy_account: { address: "" },
            slippage_bps: 200,
            builder_fee_bps: 0,
          },
          trader_settings: {
            min_self_funds: 1,
            min_copy_funds: 1,
            trading_strategy: {
              type: "order_based",
              risk_parameters: {
                blocked_assets: [],
                self_proportionality_multiplier: 1.0,
                open_on_low_pnl: { enabled: true, max_pnl: 0.05 },
              },
              bucket_config: {
                pricing_strategy: "vwap",
                auto: {
                  ratio_threshold: 1000,
                  wide_bucket_percent: 0.01,
                  narrow_bucket_percent: 0.0001,
                },
              },
            },
          },
        },
      },
    });

  const handleSubmit = async (values: CreateTraderForm) => {
    setError(null);
    try {
      const walletAddress = isEditing
        ? props.initialValues?.wallet_address
        : values.wallet_address;
      values.config.provider_settings.self_account.address = walletAddress ?? "";
      await props.onSubmit(values);
    } catch (e) {
      setError(e instanceof Error ? e.message : "An error occurred");
    }
  };

  return (
    <FormComponent onSubmit={handleSubmit} class="space-y-4">
      <Show when={error()}>
        <Alert variant="destructive">
          <AlertDescription>{error()}</AlertDescription>
        </Alert>
      </Show>

      {/* ── Account Settings panel ──────────────────────────────────────── */}
      <Panel>
        <PanelHeader
          icon={Wallet}
          title="Account Settings"
          description="Wallet, copy target & funds"
        />
        <PanelBody class="space-y-4">
          {/* Name + Description */}
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField name="name">
              {(field, fieldProps) => (
                <div class="space-y-1.5">
                  <Label for="name" class="text-xs text-text-muted">
                    Name <span class="text-text-faint">(optional)</span>
                  </Label>
                  <Input
                    {...fieldProps}
                    id="name"
                    type="text"
                    value={field.value ?? ""}
                    placeholder="e.g., Main Trading Bot"
                    maxLength={50}
                  />
                  <Show when={field.error}>
                    <p class="text-xs text-error">{field.error}</p>
                  </Show>
                </div>
              )}
            </FormField>

            <FormField name="description">
              {(field, fieldProps) => (
                <div class="space-y-1.5">
                  <Label for="description" class="text-xs text-text-muted">
                    Description <span class="text-text-faint">(optional)</span>
                  </Label>
                  <Textarea
                    {...fieldProps}
                    id="description"
                    value={field.value ?? ""}
                    onInput={(e) => fieldProps.onInput(e)}
                    onBlur={fieldProps.onBlur}
                    placeholder="Optional notes about this trader"
                    class="min-h-[36px] h-9"
                    maxLength={255}
                    rows={1}
                  />
                  <Show when={field.error}>
                    <p class="text-xs text-error">{field.error}</p>
                  </Show>
                </div>
              )}
            </FormField>
          </div>

          <Show when={!props.isEditing}>
            <FormField name="wallet_address">
              {(field, fieldProps) => (
                <div class="space-y-1.5">
                  <Label for="wallet_address" class="text-xs text-text-muted">Wallet Address</Label>
                  <Input
                    {...fieldProps}
                    id="wallet_address"
                    type="text"
                    value={field.value ?? ""}
                    placeholder="0x..."
                    class="font-mono"
                  />
                  <Show when={field.error}>
                    <p class="text-xs text-error">{field.error}</p>
                  </Show>
                </div>
              )}
            </FormField>

            <FormField name="private_key">
              {(field, fieldProps) => (
                <div class="space-y-1.5">
                  <Label for="private_key" class="text-xs text-text-muted">Private Key</Label>
                  <div class="relative">
                    <Input
                      {...fieldProps}
                      id="private_key"
                      type={showPrivateKey() ? "text" : "password"}
                      value={field.value ?? ""}
                      placeholder="0x..."
                      class="font-mono pr-10"
                    />
                    <button
                      type="button"
                      class="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary transition-colors"
                      onClick={() => setShowPrivateKey(!showPrivateKey())}
                      tabIndex={-1}
                    >
                      <Show when={showPrivateKey()} fallback={<Eye class="h-4 w-4" />}>
                        <EyeOff class="h-4 w-4" />
                      </Show>
                    </button>
                  </div>
                  <p class="text-xs text-text-muted">
                    Stored securely as a Docker secret
                  </p>
                  <Show when={field.error}>
                    <p class="text-xs text-error">{field.error}</p>
                  </Show>
                </div>
              )}
            </FormField>
          </Show>

          <FormField name="config.provider_settings.copy_account.address">
            {(field, fieldProps) => (
              <div class="space-y-1.5">
                <Label for="copy_account" class="text-xs text-text-muted">Copy Account Address</Label>
                <Input
                  {...fieldProps}
                  id="copy_account"
                  type="text"
                  value={field.value ?? ""}
                  placeholder="0x..."
                  class="font-mono"
                />
                <p class="text-xs text-text-muted">
                  The address you want to copy trades from
                </p>
                <Show when={field.error}>
                  <p class="text-xs text-error">{field.error}</p>
                </Show>
              </div>
            )}
          </FormField>

          <div class="grid grid-cols-2 gap-4">
            <FormField name="config.trader_settings.min_self_funds" type="number">
              {(field, fieldProps) => (
                <div class="space-y-1.5">
                  <Label for="min_self_funds" class="text-xs text-text-muted">Min Self Funds (USDC)</Label>
                  <Input
                    {...fieldProps}
                    id="min_self_funds"
                    type="number"
                    value={field.value ?? 1}
                    min={1}
                    step={1}
                  />
                  <Show when={field.error}>
                    <p class="text-xs text-error">{field.error}</p>
                  </Show>
                </div>
              )}
            </FormField>

            <FormField name="config.trader_settings.min_copy_funds" type="number">
              {(field, fieldProps) => (
                <div class="space-y-1.5">
                  <Label for="min_copy_funds" class="text-xs text-text-muted">Min Copy Funds (USDC)</Label>
                  <Input
                    {...fieldProps}
                    id="min_copy_funds"
                    type="number"
                    value={field.value ?? 1}
                    min={1}
                    step={1}
                  />
                  <Show when={field.error}>
                    <p class="text-xs text-error">{field.error}</p>
                  </Show>
                </div>
              )}
            </FormField>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <FormField name="config.provider_settings.network">
              {(field, fieldProps) => (
                <div class="space-y-1.5">
                  <Label for="network" class="text-xs text-text-muted">Network</Label>
                  <Select
                    id="network"
                    name={fieldProps.name}
                    ref={fieldProps.ref}
                    value={field.value ?? "mainnet"}
                    onChange={(value) => setValue(form, "config.provider_settings.network", value as "mainnet" | "testnet")}
                    options={[
                      { value: "mainnet", label: "Mainnet" },
                      { value: "testnet", label: "Testnet" },
                    ]}
                  />
                </div>
              )}
            </FormField>

            <FormField name="config.provider_settings.self_account.is_sub" type="boolean">
              {(field, fieldProps) => (
                <div class="space-y-1.5">
                  <Label class="text-xs text-text-muted">Account Type</Label>
                  <div class="flex items-center gap-2 h-9">
                    <Checkbox
                      id="is_sub"
                      checked={field.value ?? false}
                      onChange={(checked) => setValue(form, "config.provider_settings.self_account.is_sub", checked)}
                    />
                    <Label for="is_sub" class="font-normal">
                      Is Subaccount
                    </Label>
                  </div>
                </div>
              )}
            </FormField>
          </div>
        </PanelBody>
      </Panel>

      {/* ── Advanced Settings panel (collapsible) ───────────────────────── */}
      <Panel>
        <button
          type="button"
          onClick={() => setAdvancedOpen(!advancedOpen())}
          class="w-full px-5 py-3.5 flex items-center gap-2.5 text-left hover:bg-surface-overlay transition-colors"
        >
          <SlidersHorizontal class="w-4 h-4 text-text-subtle shrink-0" />
          <span class="text-sm font-medium text-text-secondary">Advanced Settings</span>
          <span class="ml-auto text-xs text-text-faint hidden sm:block">
            Strategy, risk, slippage &amp; buckets
          </span>
          <ChevronRight
            class={cn(
              "w-4 h-4 text-text-faint transition-transform duration-200 ml-2",
              advancedOpen() && "rotate-90"
            )}
          />
        </button>

        <Show when={advancedOpen()}>
          <PanelBody class="border-t border-border-default space-y-5">
            {/* Strategy section */}
            <SectionLabel label="Strategy" />
            <div class="space-y-4">
              <FormField name="config.trader_settings.trading_strategy.type">
                {(field, fieldProps) => (
                  <div class="space-y-1.5">
                    <Label for="strategy_type" class="text-xs text-text-muted">Strategy Type</Label>
                    <Select
                      id="strategy_type"
                      name={fieldProps.name}
                      ref={fieldProps.ref}
                      value={(field.value as string | undefined) ?? "order_based"}
                      onChange={(value) => setValue(form, "config.trader_settings.trading_strategy.type", value as "order_based" | "position_based")}
                      options={[
                        { value: "order_based", label: "Order Based" },
                        { value: "position_based", label: "Position Based" },
                      ]}
                    />
                  </div>
                )}
              </FormField>
            </div>

            {/* Risk Parameters section */}
            <SectionLabel label="Risk Parameters" />
            <div class="space-y-4">
              <FormField name="config.trader_settings.trading_strategy.risk_parameters.allowed_assets" type="string[]">
                {(field, _fieldProps) => (
                  <div class="space-y-1.5">
                    <Label class="text-xs text-text-muted">Allowed Assets</Label>
                    <TagInput
                      value={(field.value as string[] | null) ?? []}
                      onChange={(tags) => {
                        setValue(form, "config.trader_settings.trading_strategy.risk_parameters.allowed_assets", tags.length > 0 ? tags : null);
                      }}
                      placeholder="Type asset and press Enter (empty = all)"
                    />
                    <p class="text-xs text-text-muted">
                      Leave empty to allow all assets
                    </p>
                  </div>
                )}
              </FormField>

              <FormField name="config.trader_settings.trading_strategy.risk_parameters.blocked_assets" type="string[]">
                {(field, _fieldProps) => (
                  <div class="space-y-1.5">
                    <Label class="text-xs text-text-muted">Blocked Assets</Label>
                    <TagInput
                      value={(field.value as string[]) ?? []}
                      onChange={(tags) => {
                        setValue(form, "config.trader_settings.trading_strategy.risk_parameters.blocked_assets", tags);
                      }}
                      placeholder="Type asset and press Enter"
                    />
                  </div>
                )}
              </FormField>

              <div class="grid grid-cols-2 gap-4">
                <div class="space-y-1.5">
                  <Label class="text-xs text-text-muted">Max Leverage</Label>
                  <div class="flex items-center gap-2">
                    <Checkbox
                      id="max_leverage_toggle"
                      checked={maxLeverageEnabled()}
                      onChange={(checked) => {
                        setMaxLeverageEnabled(checked);
                        if (!checked) {
                          setValue(form, "config.trader_settings.trading_strategy.risk_parameters.max_leverage", null);
                        } else {
                          setValue(form, "config.trader_settings.trading_strategy.risk_parameters.max_leverage", 10);
                        }
                      }}
                    />
                    <Label for="max_leverage_toggle" class="font-normal">
                      Set max leverage
                    </Label>
                  </div>
                  <Show when={maxLeverageEnabled()}>
                    <FormField name="config.trader_settings.trading_strategy.risk_parameters.max_leverage" type="number">
                      {(field, fieldProps) => (
                        <Input
                          {...fieldProps}
                          id="max_leverage"
                          type="number"
                          value={field.value ?? 10}
                          min={1}
                          max={50}
                        />
                      )}
                    </FormField>
                  </Show>
                </div>

                <FormField name="config.trader_settings.trading_strategy.risk_parameters.self_proportionality_multiplier" type="number">
                  {(field, fieldProps) => (
                    <div class="space-y-1.5">
                      <Label for="multiplier" class="text-xs text-text-muted">Size Multiplier</Label>
                      <Input
                        {...fieldProps}
                        id="multiplier"
                        type="number"
                        value={field.value ?? 1.0}
                        min={0.01}
                        max={10}
                        step={0.1}
                      />
                    </div>
                  )}
                </FormField>
              </div>

              <div class="grid grid-cols-2 gap-4">
                <FormField name="config.trader_settings.trading_strategy.risk_parameters.open_on_low_pnl.enabled" type="boolean">
                  {(field, _fieldProps) => (
                    <div class="flex items-center gap-2">
                      <Checkbox
                        checked={field.value ?? true}
                        onChange={(checked) => setValue(form, "config.trader_settings.trading_strategy.risk_parameters.open_on_low_pnl.enabled", checked)}
                      />
                      <Label class="font-normal">Open on Low PnL</Label>
                    </div>
                  )}
                </FormField>

                <FormField name="config.trader_settings.trading_strategy.risk_parameters.open_on_low_pnl.max_pnl" type="number">
                  {(field, fieldProps) => (
                    <div class="space-y-1.5">
                      <Label for="max_pnl" class="text-xs text-text-muted">Max PnL Threshold (%)</Label>
                      <Input
                        {...fieldProps}
                        id="max_pnl"
                        type="number"
                        value={parseFloat(((field.value ?? 0.05) * 100).toFixed(4))}
                        onInput={(e) => {
                          const pctVal = parseFloat((e.target as HTMLInputElement).value);
                          setValue(
                            form,
                            "config.trader_settings.trading_strategy.risk_parameters.open_on_low_pnl.max_pnl",
                            isNaN(pctVal) ? 0.05 : pctVal / 100
                          );
                        }}
                        min={-100}
                        max={100}
                        step={0.1}
                      />
                    </div>
                  )}
                </FormField>
              </div>
            </div>

            {/* Slippage & Fees section */}
            <SectionLabel label="Slippage & Fees" />
            <div class="space-y-4">
              <FormField name="config.provider_settings.slippage_bps" type="number">
                {(field, fieldProps) => (
                  <div class="space-y-1.5">
                    <Label for="slippage" class="text-xs text-text-muted">Slippage (bps)</Label>
                    <Input
                      {...fieldProps}
                      id="slippage"
                      type="number"
                      value={field.value ?? 200}
                      min={0}
                      max={1000}
                    />
                    <p class="text-xs text-text-muted">1 bp = 0.01%</p>
                  </div>
                )}
              </FormField>
            </div>

            {/* Bucket Configuration section */}
            <SectionLabel label="Bucket Configuration" />
            <div class="space-y-4">
              <ToggleGroup
                options={[
                  { value: "manual", label: "Manual" },
                  { value: "auto", label: "Auto" },
                ]}
                value={bucketMode()}
                onChange={(v) => setBucketMode(v as "manual" | "auto")}
              />

              <Show when={bucketMode() === "manual"}>
                {/* @ts-expect-error - bucket_config.manual path exists when bucketMode is "manual" */}
                <FormField name="config.trader_settings.trading_strategy.bucket_config.manual.width_percent" type="number">
                  {(field, fieldProps) => (
                    <div class="space-y-1.5">
                      <Label for="width_percent" class="text-xs text-text-muted">Width Percent</Label>
                      <Input
                        {...fieldProps}
                        id="width_percent"
                        type="number"
                        value={field.value ?? 0.01}
                        min={0.0001}
                        max={1}
                        step={0.001}
                      />
                    </div>
                  )}
                </FormField>
              </Show>

              <Show when={bucketMode() === "auto"}>
                <div class="grid grid-cols-3 gap-4">
                  {/* @ts-expect-error - bucket_config.auto path exists when bucketMode is "auto" */}
                  <FormField name="config.trader_settings.trading_strategy.bucket_config.auto.ratio_threshold" type="number">
                    {(field, fieldProps) => (
                      <div class="space-y-1.5">
                        <Label for="ratio_threshold" class="text-xs text-text-muted">Ratio Threshold</Label>
                        <Input
                          {...fieldProps}
                          id="ratio_threshold"
                          type="number"
                          value={field.value ?? 1000}
                          min={0.1}
                        />
                      </div>
                    )}
                  </FormField>

                  {/* @ts-expect-error - bucket_config.auto path exists when bucketMode is "auto" */}
                  <FormField name="config.trader_settings.trading_strategy.bucket_config.auto.wide_bucket_percent" type="number">
                    {(field, fieldProps) => (
                      <div class="space-y-1.5">
                        <Label for="wide_bucket" class="text-xs text-text-muted">Wide Bucket %</Label>
                        <Input
                          {...fieldProps}
                          id="wide_bucket"
                          type="number"
                          value={field.value ?? 0.01}
                          min={0.0001}
                          max={1}
                          step={0.001}
                        />
                      </div>
                    )}
                  </FormField>

                  {/* @ts-expect-error - bucket_config.auto path exists when bucketMode is "auto" */}
                  <FormField name="config.trader_settings.trading_strategy.bucket_config.auto.narrow_bucket_percent" type="number">
                    {(field, fieldProps) => (
                      <div class="space-y-1.5">
                        <Label for="narrow_bucket" class="text-xs text-text-muted">Narrow Bucket %</Label>
                        <Input
                          {...fieldProps}
                          id="narrow_bucket"
                          type="number"
                          value={field.value ?? 0.0001}
                          min={0.00001}
                          max={1}
                          step={0.0001}
                        />
                      </div>
                    )}
                  </FormField>
                </div>
              </Show>

              <FormField name="config.trader_settings.trading_strategy.bucket_config.pricing_strategy" type="string">
                {(field, fieldProps) => (
                  <div class="space-y-1.5">
                    <Label for="pricing_strategy" class="text-xs text-text-muted">Pricing Strategy</Label>
                    <Select
                      id="pricing_strategy"
                      name={fieldProps.name}
                      ref={fieldProps.ref}
                      value={(field.value as string | undefined) ?? "vwap"}
                      onChange={(value) => {
                        setValue(form, "config.trader_settings.trading_strategy.bucket_config.pricing_strategy", value as "vwap" | "aggressive");
                      }}
                      options={[
                        { value: "vwap", label: "VWAP" },
                        { value: "aggressive", label: "Aggressive" },
                      ]}
                    />
                  </div>
                )}
              </FormField>
            </div>
          </PanelBody>
        </Show>
      </Panel>

      {/* Submit Button */}
      <div class="flex justify-end">
        <Button type="submit" disabled={props.isSubmitting}>
          {props.isSubmitting ? "Saving..." : (props.submitLabel ?? "Create Trader")}
        </Button>
      </div>
    </FormComponent>
  );
};
