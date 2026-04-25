import { type Component, For, createSignal } from "solid-js";
import { X } from "lucide-solid";
import { cn } from "~/lib/utils";
import { Badge } from "./badge";
import { Input } from "./input";

export interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
  class?: string;
  id?: string;
}

export const TagInput: Component<TagInputProps> = (props) => {
  const [inputValue, setInputValue] = createSignal("");

  const addTag = (tag: string) => {
    const trimmed = tag.trim().toUpperCase();
    if (trimmed && !props.value.includes(trimmed)) {
      props.onChange([...props.value, trimmed]);
    }
    setInputValue("");
  };

  const removeTag = (index: number) => {
    props.onChange(props.value.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag(inputValue());
    } else if (
      e.key === "Backspace" &&
      !inputValue() &&
      props.value.length > 0
    ) {
      removeTag(props.value.length - 1);
    }
  };

  return (
    <div
      class={cn(
        "flex flex-wrap gap-2 p-2 rounded-md border border-input bg-transparent min-h-[42px]",
        props.disabled && "opacity-50 cursor-not-allowed",
        props.class
      )}
    >
      <For each={props.value}>
        {(tag, index) => (
          <Badge variant="secondary" class="gap-1 pr-1">
            {tag}
            <button
              type="button"
              onClick={() => removeTag(index())}
              disabled={props.disabled}
              class="ml-1 rounded-full hover:bg-muted-foreground/20 p-0.5"
            >
              <X class="h-3 w-3" />
            </button>
          </Badge>
        )}
      </For>
      <Input
        id={props.id}
        type="text"
        value={inputValue()}
        onInput={(e) => setInputValue(e.currentTarget.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => inputValue() && addTag(inputValue())}
        placeholder={props.value.length === 0 ? props.placeholder : ""}
        disabled={props.disabled}
        class="flex-1 min-w-[120px] border-0 shadow-none focus-visible:ring-0 p-0 h-auto"
      />
    </div>
  );
};
