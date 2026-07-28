import mongoose from "mongoose";

const SizeSchema = new mongoose.Schema(
  {
    name: { type: String, required: true },
    priceModifier: { type: Number, required: true, default: 0 },
  },
  { _id: false }
);

const AddonSchema = new mongoose.Schema(
  {
    name: { type: String, required: true },
    price: { type: Number, required: true, min: 0 },
  },
  { _id: false }
);

const SwapSchema = new mongoose.Schema(
  {
    itemId: { type: String, required: true },
    priceModifier: { type: Number, required: true, default: 0 },
  },
  { _id: false }
);

const ComponentSchema = new mongoose.Schema(
  {
    slot: { type: String, required: true },
    default: { type: String, default: null },
    quantity: { type: Number, default: 1, min: 1 },
    swappable: { type: Boolean, required: true, default: false },
    allowedSwaps: { type: [SwapSchema], default: [] },
  },
  { _id: false }
);

const MenuItemSchema = new mongoose.Schema(
  {
    itemId: { type: String, required: true, unique: true, index: true },
    name: { type: String, required: true },
    aliases: { type: [String], default: [] },
    category: {
      type: String,
      required: true,
      enum: ["burgers", "chicken", "sides", "drinks", "desserts", "meals"],
      index: true,
    },
    description: { type: String, default: "" },
    basePrice: { type: Number, required: true, min: 0 },
    available: { type: Boolean, required: true, default: true },
    sizes: { type: [SizeSchema], default: [] },
    removableIngredients: { type: [String], default: [] },
    addons: { type: [AddonSchema], default: [] },
    components: { type: [ComponentSchema], default: [] },
    maxQuantityPerOrder: { type: Number, default: 10, min: 1 },
    embedding: { type: [Number], default: undefined }, // set by buildEmbeddings.js (Version B)
  },
  { timestamps: true }
);

MenuItemSchema.index({ name: "text", aliases: "text" });

export const MenuItem = mongoose.model("MenuItem", MenuItemSchema);
