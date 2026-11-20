package com.mox1x.aethertech.content.element;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.mox1x.aethertech.AetherTech;
import com.mox1x.aethertech.component.CompositionComponent;
import com.mox1x.aethertech.component.ModDataComponents;
import com.mox1x.aethertech.content.item.ElementFormBlockItem;
import com.mox1x.aethertech.content.item.ElementFormItem;
import com.mox1x.aethertech.util.BuiltinJsonResourceLoader;

import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.neoforged.neoforge.registries.DeferredBlock;
import net.neoforged.neoforge.registries.DeferredItem;
import net.neoforged.neoforge.registries.DeferredRegister;

public final class AetherTechElementForms {
    private static final String CATALOG_RESOURCE = "data/" + AetherTech.MODID + "/material_forms/elements.json";

    private static final Map<String, DeferredItem<? extends Item>> REGISTERED_ITEMS = new LinkedHashMap<>();
    private static boolean bootstrapped = false;

    private AetherTechElementForms() {
    }

    public static void bootstrap(DeferredRegister.Blocks blocks, DeferredRegister.Items items) {
        if (bootstrapped) {
            return;
        }

        List<ElementFormDefinition> catalog = loadCatalog();
        if (catalog.isEmpty()) {
            AetherTech.LOGGER.warn("Element form catalog is empty or missing at {}. No generated element form items were registered.", CATALOG_RESOURCE);
            bootstrapped = true;
            return;
        }

        for (ElementFormDefinition definition : catalog) {
            DeferredItem<? extends Item> item = registerDefinition(definition, blocks, items);
            REGISTERED_ITEMS.put(definition.itemId(), item);
        }

        bootstrapped = true;
    }

    public static List<DeferredItem<? extends Item>> registeredCreativeItems() {
        return List.copyOf(REGISTERED_ITEMS.values());
    }

    public static ItemStack iconStack() {
        for (String preferredId : List.of("ferrum_ingot", "cuprum_ingot", "argentum_ingot", "aurum_ingot")) {
            DeferredItem<? extends Item> item = REGISTERED_ITEMS.get(preferredId);
            if (item != null) {
                return item.get().getDefaultInstance();
            }
        }

        return REGISTERED_ITEMS.values().stream()
            .findFirst()
            .map(holder -> holder.get().getDefaultInstance())
            .orElse(ItemStack.EMPTY);
    }

    public static int size() {
        return REGISTERED_ITEMS.size();
    }

    private static DeferredItem<? extends Item> registerDefinition(
        ElementFormDefinition definition,
        DeferredRegister.Blocks blocks,
        DeferredRegister.Items items
    ) {
        if ("metal_block".equals(definition.form())) {
            DeferredBlock<Block> block = blocks.register(
                definition.itemId(),
                id -> new Block(
                    BlockBehaviour.Properties.ofFullCopy(Blocks.IRON_BLOCK)
                        .setId(ResourceKey.create(Registries.BLOCK, id))
                )
            );
            return items.register(
                definition.itemId(),
                id -> new ElementFormBlockItem(
                    block.get(),
                    definition.displayName(),
                    compositionProperties(definition)
                        .setId(ResourceKey.create(Registries.ITEM, id))
                )
            );
        }

        return items.registerItem(
            definition.itemId(),
            itemProperties -> new ElementFormItem(definition.displayName(), itemProperties),
            () -> compositionProperties(definition)
        );
    }

    private static Item.Properties compositionProperties(ElementFormDefinition definition) {
        return new Item.Properties().component(
            ModDataComponents.COMPOSITION.get(),
            new CompositionComponent(Map.of(definition.symbol(), 1.0F), definition.symbol())
        );
    }

    private static List<ElementFormDefinition> loadCatalog() {
        return BuiltinJsonResourceLoader.loadObject(CATALOG_RESOURCE)
            .map(AetherTechElementForms::parseCatalog)
            .orElse(List.of());
    }

    private static List<ElementFormDefinition> parseCatalog(JsonObject root) {
        JsonArray entries = root.getAsJsonArray("entries");
        if (entries == null) {
            throw new IllegalStateException("Missing entries array in " + CATALOG_RESOURCE);
        }

        List<ElementFormDefinition> catalog = new java.util.ArrayList<>(entries.size());
        for (int index = 0; index < entries.size(); index++) {
            JsonObject entry = entries.get(index).getAsJsonObject();
            catalog.add(ElementFormDefinition.fromJson(Identifier.fromNamespaceAndPath(AetherTech.MODID, "material_forms/" + index), entry));
        }
        return List.copyOf(catalog);
    }
}
