import { type Component, createSignal, Show } from "solid-js";
import { createForm, setValue } from "@modular-forms/solid";
import {
  Eye,
  EyeOff,
  ChevronRight,
  Wallet,
  SlidersHorizontal,
  RotateCcw,
  Info,
} from "lucide-solid";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { Select } from "~/components/ui/select";
import { Switch } from "~/components/ui/switch";
import { TagInput } from "~/components/ui/tag-input";
import { Panel, PanelHeader, PanelBody } from "~/components/ui/panel";
import { SectionLabel } from "~/components/ui/section-label";
import { ToggleGroup } from "~/components/ui/toggle-group";
import { Textarea } from "~/components/ui/textarea";
import { FormGrid } from "~/components/ui/form-grid";
import { cn } from "~/lib/utils";
import {
  buildInitialTraderForm,
  deepMergeFormValues,
  prepareTraderFormValues,
  TRADER_FORM_DEFAULTS,
  validateTraderForm,
  type TraderFormMode,
  type TraderFormValues,
} from "./trader-form-model";

export interface TraderFormProps {
  mode: TraderFormMode;
  initialValues?: TraderFormValues;
  onSubmit: (data: TraderFormValues) => Promise<void>;
  isSubmitting?: boolean;
  submitLabel?: string;
}

const ASSET_SELECTOR_HELP = '"*" loads all markets. Examples: BTC = default:BTC, default:* loads default market, xyz:* loads xyz market. Block wins over allow.';

const bpsToPercent = (bps: number) => parseFloat((bps / 100).toFixed(4));
const percentToBps = (percent: number) => Math.round(percent * 100);

export const TraderForm: Component<TraderFormProps> = (props) => {
  const [error, setError] = createSignal<string | null>(null);
  const [showPrivateKey, setShowPrivateKey] = createSignal(false);
  const initialValues = props.initialValues ?? buildInitialTraderForm(props.mode);
  const isEditing = () => props.mode === "edit";
  const [bucketMode, setBucketMode] = createSignal<"manual" | "auto">(
    initialValues.config.trader_settings.trading_strategy.bucket_config.type
  );
  const [advancedOpen, setAdvancedOpen] = createSignal(false);
  const [maxLeverageEnabled, setMaxLeverageEnabled] = createSignal(
    (initialValues.config.provider_settings.risk_parameters.max_leverage ?? null) !== null
  );

  const [form, { Form: FormComponent, Field: FormField }] =
    createForm<TraderFormValues>({
      validate: (values) => validateTraderForm(props.mode, initialValues, values),
      initialValues,
    });

  const handleSubmit = async (values: TraderFormValues) => {
    setError(null);
    try {
      const merged = deepMergeFormValues(initialValues, values);
      await props.onSubmit(prepareTraderFormValues(merged));
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
          description="Wallet, copy target"
        />
        <PanelBody class="space-y-4">
          <FormGrid>
            <FormField name="name">
              {(field, fieldProps) => (
                <div class="space-y-1.5">
                  <Label for="name" class="text-xs text-text-muted">
                    Name <span aria-hidden="true" class="text-text-faint">(optional)</span>
                  </Label>
                  <Input
                    {...fieldProps}
                    id="name"
                    aria-label="Name"
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
                    Description <span aria-hidden="true" class="text-text-faint">(optional)</span>
                  </Label>
                  <Textarea
                    {...fieldProps}
                    id="description"
                    aria-label="Description"
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
          </FormGrid>

          <Show when={!isEditing()}>
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

          <FormGrid>
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
              {(field, _fieldProps) => (
                <div class="space-y-1.5">
                  <Label class="text-xs text-text-muted">Account Type</Label>
                  <div class="flex h-9 items-center justify-between rounded-md border border-border-default bg-surface-raised px-3">
                    <Label for="is_sub" class="text-sm text-text-secondary font-normal cursor-pointer">
                      Is Subaccount
                    </Label>
                    <Switch
                      id="is_sub"
                      checked={field.value ?? false}
                      onChange={(checked) => setValue(form, "config.provider_settings.self_account.is_sub", checked)}
                    />
                  </div>
                </div>
              )}
            </FormField>
          </FormGrid>

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
            <div class="space-y-1.5">
              <Label class="text-xs text-text-muted">Strategy Type</Label>
              <div class="h-9 rounded-md border border-border-default bg-surface-raised px-3 py-2 text-sm text-text-secondary">
                Order Based
              </div>
            </div>

            {/* Risk Parameters section */}
            <SectionLabel label="Risk Parameters" />
            <div class="space-y-4">
              <FormField name="config.provider_settings.risk_parameters.allowed_assets" type="string[]">
                {(field, _fieldProps) => (
                  <div class="space-y-1.5">
                    <div class="flex items-center gap-1.5">
                      <Label class="text-xs text-text-muted">Allowed Assets</Label>
                      <button type="button" aria-label="Allowed Assets help" title={ASSET_SELECTOR_HELP} class="text-text-faint hover:text-text-muted">
                        <Info class="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <TagInput
                      value={Array.isArray(field.value) ? field.value : []}
                      onChange={(tags) => {
                        setValue(form, "config.provider_settings.risk_parameters.allowed_assets", tags.length > 0 ? tags : "*");
                      }}
                      placeholder="Type selector and press Enter (empty = *)"
                    />
                    <p class="text-xs text-text-muted">
                      Empty means all markets. Use selectors like BTC, default:*, xyz:*.
                    </p>
                  </div>
                )}
              </FormField>

              <FormField name="config.provider_settings.risk_parameters.blocked_assets" type="string[]">
                {(field, _fieldProps) => (
                  <div class="space-y-1.5">
                    <div class="flex items-center gap-1.5">
                      <Label class="text-xs text-text-muted">Blocked Assets</Label>
                      <button type="button" aria-label="Blocked Assets help" title={ASSET_SELECTOR_HELP} class="text-text-faint hover:text-text-muted">
                        <Info class="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <TagInput
                      value={(field.value as string[]) ?? []}
                      onChange={(tags) => {
                        setValue(form, "config.provider_settings.risk_parameters.blocked_assets", tags);
                      }}
                      placeholder="Type selector and press Enter"
                    />
                  </div>
                )}
              </FormField>

              <FormGrid>
                <div class="space-y-2">
                  <Label class="text-xs text-text-muted">Max Leverage</Label>
                  <div class="flex items-center justify-between rounded-md border border-border-default bg-surface-raised px-3 h-9">
                    <Label for="max_leverage_toggle" class="text-sm text-text-secondary font-normal cursor-pointer">
                      Set max leverage
                    </Label>
                    <Switch
                      id="max_leverage_toggle"
                      checked={maxLeverageEnabled()}
                      onChange={(checked) => {
                        setMaxLeverageEnabled(checked);
                        if (!checked) {
                          setValue(form, "config.provider_settings.risk_parameters.max_leverage", null);
                        } else {
                          setValue(form, "config.provider_settings.risk_parameters.max_leverage", TRADER_FORM_DEFAULTS.maxLeverage);
                        }
                      }}
                    />
                  </div>
                  <Show when={maxLeverageEnabled()}>
                    <FormField name="config.provider_settings.risk_parameters.max_leverage" type="number">
                      {(field, fieldProps) => (
                        <>
                          <Input
                            {...fieldProps}
                            id="max_leverage"
                            type="number"
                            value={field.value ?? TRADER_FORM_DEFAULTS.maxLeverage}
                            min={TRADER_FORM_DEFAULTS.maxLeverageMin}
                            max={TRADER_FORM_DEFAULTS.maxLeverageMax}
                          />
                          <Show when={field.error}>
                            <p class="text-xs text-error">{field.error}</p>
                          </Show>
                        </>
                      )}
                    </FormField>
                  </Show>
                  <Show when={!maxLeverageEnabled()}>
                    <FormField name="config.provider_settings.risk_parameters.max_leverage">
                      {() => null}
                    </FormField>
                  </Show>
                </div>

                <FormField name="config.trader_settings.trading_strategy.risk_parameters.self_proportionality_multiplier" type="number">
                  {(field, fieldProps) => (
                    <div class="space-y-1.5">
                      <div class="flex items-center justify-between">
                        <Label for="multiplier" class="text-xs text-text-muted">Size Multiplier</Label>
                        <button type="button" title={`Restore default (${TRADER_FORM_DEFAULTS.multiplier})`} class="text-text-faint hover:text-text-muted transition-colors" onClick={() => setValue(form, "config.trader_settings.trading_strategy.risk_parameters.self_proportionality_multiplier", TRADER_FORM_DEFAULTS.multiplier)}>
                          <RotateCcw class="h-3 w-3" />
                        </button>
                      </div>
                      <Input
                        {...fieldProps}
                        id="multiplier"
                        type="number"
                        value={field.value ?? TRADER_FORM_DEFAULTS.multiplier}
                        min={0.01}
                        max={10}
                        step={0.1}
                      />
                      <Show when={field.error}>
                        <p class="text-xs text-error">{field.error}</p>
                      </Show>
                    </div>
                  )}
                </FormField>
              </FormGrid>

              <FormGrid>
                <FormField name="config.trader_settings.trading_strategy.risk_parameters.open_on_low_pnl.enabled" type="boolean">
                  {(field, _fieldProps) => (
                    <div class="space-y-1.5">
                      <Label class="text-xs text-text-muted">Open on Low PnL</Label>
                      <div class="flex items-center justify-between rounded-md border border-border-default bg-surface-raised px-3 h-9">
                        <Label class="text-sm text-text-secondary font-normal">
                          Enabled
                        </Label>
                        <Switch
                          checked={field.value ?? true}
                          onChange={(checked) => setValue(form, "config.trader_settings.trading_strategy.risk_parameters.open_on_low_pnl.enabled", checked)}
                        />
                      </div>
                    </div>
                  )}
                </FormField>

                <FormField name="config.trader_settings.trading_strategy.risk_parameters.open_on_low_pnl.max_pnl" type="number">
                  {(field, fieldProps) => (
                    <div class="space-y-1.5">
                      <div class="flex items-center justify-between">
                        <Label for="max_pnl" class="text-xs text-text-muted">Max PnL Threshold (%)</Label>
                        <button type="button" title={`Restore default (${TRADER_FORM_DEFAULTS.maxPnl * 100}%)`} class="text-text-faint hover:text-text-muted transition-colors" onClick={() => setValue(form, "config.trader_settings.trading_strategy.risk_parameters.open_on_low_pnl.max_pnl", TRADER_FORM_DEFAULTS.maxPnl)}>
                          <RotateCcw class="h-3 w-3" />
                        </button>
                      </div>
                      <Input
                        {...fieldProps}
                        id="max_pnl"
                        type="number"
                        value={parseFloat(((field.value ?? TRADER_FORM_DEFAULTS.maxPnl) * 100).toFixed(4))}
                        onInput={(e) => {
                          const pctVal = parseFloat((e.target as HTMLInputElement).value);
                          setValue(
                            form,
                            "config.trader_settings.trading_strategy.risk_parameters.open_on_low_pnl.max_pnl",
                            isNaN(pctVal) ? TRADER_FORM_DEFAULTS.maxPnl : pctVal / 100
                          );
                        }}
                        min={-100}
                        max={100}
                        step={1}
                      />
                      <Show when={field.error}>
                        <p class="text-xs text-error">{field.error}</p>
                      </Show>
                    </div>
                  )}
                </FormField>
              </FormGrid>
            </div>

            {/* Slippage section */}
            <SectionLabel label="Slippage" />
            <div class="space-y-4">
              <FormField name="config.provider_settings.slippage_bps" type="number">
                {(field, fieldProps) => (
                  <div class="space-y-1.5">
                    <div class="flex items-center justify-between">
                      <Label for="slippage" class="text-xs text-text-muted">Slippage (%)</Label>
                      <button type="button" title={`Restore default (${bpsToPercent(TRADER_FORM_DEFAULTS.slippageBps)}%)`} class="text-text-faint hover:text-text-muted transition-colors" onClick={() => setValue(form, "config.provider_settings.slippage_bps", TRADER_FORM_DEFAULTS.slippageBps)}>
                        <RotateCcw class="h-3 w-3" />
                      </button>
                    </div>
                    <Input
                      {...fieldProps}
                      id="slippage"
                      type="number"
                      value={bpsToPercent(field.value ?? TRADER_FORM_DEFAULTS.slippageBps)}
                      onInput={(e) => {
                        const percent = parseFloat((e.target as HTMLInputElement).value);
                        setValue(
                          form,
                          "config.provider_settings.slippage_bps",
                          isNaN(percent) ? TRADER_FORM_DEFAULTS.slippageBps : percentToBps(percent)
                        );
                      }}
                      min={0}
                      max={10}
                      step={0.01}
                    />
                    <Show when={field.error}>
                      <p class="text-xs text-error">{field.error}</p>
                    </Show>
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
                onChange={(v) => {
                  const mode = v as "manual" | "auto";
                  setBucketMode(mode);
                  setValue(
                    form,
                    "config.trader_settings.trading_strategy.bucket_config" as never,
                    (mode === "manual"
                      ? { type: "manual", width_percent: TRADER_FORM_DEFAULTS.widthPercent, pricing_strategy: "vwap" }
                      : {
                        type: "auto",
                        ratio_threshold: TRADER_FORM_DEFAULTS.ratioThreshold,
                        wide_bucket_percent: TRADER_FORM_DEFAULTS.wideBucketPct,
                        narrow_bucket_percent: TRADER_FORM_DEFAULTS.narrowBucketPct,
                        pricing_strategy: "vwap",
                      }) as never
                  );
                }}
              />

              <Show when={bucketMode() === "manual"}>
                <FormField name={"config.trader_settings.trading_strategy.bucket_config.width_percent" as never}>
                  {(field, fieldProps) => (
                    <div class="space-y-1.5">
                      <div class="flex items-center justify-between">
                        <Label for="width_percent" class="text-xs text-text-muted">Width Percent</Label>
                        <button type="button" title={`Restore default (${TRADER_FORM_DEFAULTS.widthPercent})`} class="text-text-faint hover:text-text-muted transition-colors" onClick={() => setValue(form, "config.trader_settings.trading_strategy.bucket_config.width_percent" as never, TRADER_FORM_DEFAULTS.widthPercent as never)}>
                          <RotateCcw class="h-3 w-3" />
                        </button>
                      </div>
                      <Input
                        {...fieldProps}
                        id="width_percent"
                        type="number"
                        value={field.value ?? TRADER_FORM_DEFAULTS.widthPercent}
                        min={0.0001}
                        max={1}
                        step={0.001}
                      />
                      <Show when={field.error}>
                        <p class="text-xs text-error">{field.error}</p>
                      </Show>
                    </div>
                  )}
                </FormField>
              </Show>

              <Show when={bucketMode() === "auto"}>
                <FormGrid cols={3}>
                  <FormField name={"config.trader_settings.trading_strategy.bucket_config.ratio_threshold" as never}>
                    {(field, fieldProps) => (
                      <div class="space-y-1.5">
                        <div class="flex items-center justify-between">
                          <Label for="ratio_threshold" class="text-xs text-text-muted">Ratio Threshold</Label>
                          <button type="button" title={`Restore default (${TRADER_FORM_DEFAULTS.ratioThreshold})`} class="text-text-faint hover:text-text-muted transition-colors" onClick={() => setValue(form, "config.trader_settings.trading_strategy.bucket_config.ratio_threshold" as never, TRADER_FORM_DEFAULTS.ratioThreshold as never)}>
                            <RotateCcw class="h-3 w-3" />
                          </button>
                        </div>
                        <Input
                          {...fieldProps}
                          id="ratio_threshold"
                          type="number"
                          value={field.value ?? TRADER_FORM_DEFAULTS.ratioThreshold}
                          min={0.1}
                        />
                        <Show when={field.error}>
                          <p class="text-xs text-error">{field.error}</p>
                        </Show>
                      </div>
                    )}
                  </FormField>

                  <FormField name={"config.trader_settings.trading_strategy.bucket_config.wide_bucket_percent" as never}>
                    {(field, fieldProps) => (
                      <div class="space-y-1.5">
                        <div class="flex items-center justify-between">
                          <Label for="wide_bucket" class="text-xs text-text-muted">Wide Bucket %</Label>
                          <button type="button" title={`Restore default (${TRADER_FORM_DEFAULTS.wideBucketPct})`} class="text-text-faint hover:text-text-muted transition-colors" onClick={() => setValue(form, "config.trader_settings.trading_strategy.bucket_config.wide_bucket_percent" as never, TRADER_FORM_DEFAULTS.wideBucketPct as never)}>
                            <RotateCcw class="h-3 w-3" />
                          </button>
                        </div>
                        <Input
                          {...fieldProps}
                          id="wide_bucket"
                          type="number"
                          value={field.value ?? TRADER_FORM_DEFAULTS.wideBucketPct}
                          min={0.0001}
                          max={1}
                          step={0.001}
                        />
                        <Show when={field.error}>
                          <p class="text-xs text-error">{field.error}</p>
                        </Show>
                      </div>
                    )}
                  </FormField>

                  <FormField name={"config.trader_settings.trading_strategy.bucket_config.narrow_bucket_percent" as never}>
                    {(field, fieldProps) => (
                      <div class="space-y-1.5">
                        <div class="flex items-center justify-between">
                          <Label for="narrow_bucket" class="text-xs text-text-muted">Narrow Bucket %</Label>
                          <button type="button" title={`Restore default (${TRADER_FORM_DEFAULTS.narrowBucketPct})`} class="text-text-faint hover:text-text-muted transition-colors" onClick={() => setValue(form, "config.trader_settings.trading_strategy.bucket_config.narrow_bucket_percent" as never, TRADER_FORM_DEFAULTS.narrowBucketPct as never)}>
                            <RotateCcw class="h-3 w-3" />
                          </button>
                        </div>
                        <Input
                          {...fieldProps}
                          id="narrow_bucket"
                          type="number"
                          value={field.value ?? TRADER_FORM_DEFAULTS.narrowBucketPct}
                          min={0.00001}
                          max={1}
                          step={0.0001}
                        />
                        <Show when={field.error}>
                          <p class="text-xs text-error">{field.error}</p>
                        </Show>
                      </div>
                    )}
                  </FormField>
                </FormGrid>
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

export const TraderConfigForm = TraderForm;
