package io.github.kriscs1.shardsofashen;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;

import com.android.billingclient.api.AcknowledgePurchaseParams;
import com.android.billingclient.api.BillingClient;
import com.android.billingclient.api.BillingClientStateListener;
import com.android.billingclient.api.BillingFlowParams;
import com.android.billingclient.api.BillingResult;
import com.android.billingclient.api.PendingPurchasesParams;
import com.android.billingclient.api.ProductDetails;
import com.android.billingclient.api.Purchase;
import com.android.billingclient.api.QueryProductDetailsParams;
import com.android.billingclient.api.QueryPurchasesParams;

/** What's bought through Google Play, each a one-time product made in the Play Console: the full game
 *  (BuildConfig.FULL_PRODUCT: the whole world and no level cap, and no ads either) and "Remove ads" on its own
 *  (BuildConfig.ADFREE_PRODUCT). Bought, it's this device's at once (Single player needs no account), and Google Play
 *  gives it back after a reinstall or on another phone with the same Google account (its purchases are asked for each
 *  time the app opens). The full game's purchase token is kept for the start screen to send the central server, which
 *  checks it with Google Play before it's the Hallisium account's too (central/bought.py). The payment is Google's: the
 *  app never sees a card. The start screen is told when one's bought ("full", "bought"), pending, or failed. */
class Billing {
    static final String FULL = BuildConfig.FULL_PRODUCT, ADFREE = BuildConfig.ADFREE_PRODUCT;

    private final Activity activity;
    private final Consumer<String> told;              // ("full", "bought" (no ads), "pending", or "failed")
    private BillingClient client;
    private final Map<String, ProductDetails> products = new ConcurrentHashMap<>();
    private final Map<String, String> prices = new ConcurrentHashMap<>();
    private volatile boolean adFree, full;

    Billing(Activity activity, Consumer<String> told) {
        this.activity = activity;
        this.told = told;
        adFree = prefs().getBoolean("ad_free", false);  // (known at once, before Google Play answers)
        full = prefs().getBoolean("full_game", false);
    }

    static boolean on() {
        return !FULL.isEmpty() || !ADFREE.isEmpty();
    }

    private SharedPreferences prefs() {
        return activity.getSharedPreferences("start", Context.MODE_PRIVATE);
    }

    /** No ads: either bought. */
    boolean adFree() {
        return adFree || full;
    }

    boolean full() {
        return full;
    }

    /** The full game's purchase token, for the central server ("" if it isn't bought here). */
    String fullToken() {
        return full ? prefs().getString("full_token", "") : "";
    }

    /** A product's price as Google Play shows it here ("£3.49"), or "" until it's known (or it's had already, or there
     *  isn't one in this build). */
    String price(String id) {
        if (id.isEmpty() || full || (id.equals(ADFREE) && adFree)) return "";
        String p = prices.get(id);
        return p == null ? "" : p;
    }

    void start() {
        if (!on()) return;
        client = BillingClient.newBuilder(activity)
            .setListener((result, purchases) -> {
                if (result.getResponseCode() == BillingClient.BillingResponseCode.OK && purchases != null) {
                    for (Purchase p : purchases) took(p);
                } else if (result.getResponseCode() == BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED) {
                    restore();
                } else if (result.getResponseCode() != BillingClient.BillingResponseCode.USER_CANCELED) {
                    told.accept("failed");
                }
            })
            .enablePendingPurchases(PendingPurchasesParams.newBuilder().enableOneTimeProducts().build())
            .build();
        connect();
    }

    private void connect() {
        client.startConnection(new BillingClientStateListener() {
            @Override
            public void onBillingSetupFinished(BillingResult result) {
                if (result.getResponseCode() != BillingClient.BillingResponseCode.OK) return;
                restore();
                details();
            }

            @Override
            public void onBillingServiceDisconnected() {
                // (asked again the next time a button's pressed)
            }
        });
    }

    /** What this Google account has bought: given back after a reinstall, or taken away after a refund. */
    private void restore() {
        client.queryPurchasesAsync(QueryPurchasesParams.newBuilder().setProductType(BillingClient.ProductType.INAPP).build(),
            (result, purchases) -> {
                if (result.getResponseCode() != BillingClient.BillingResponseCode.OK) return;
                boolean hasFull = false, hasAdFree = false;
                for (Purchase p : purchases) {
                    if (p.getPurchaseState() != Purchase.PurchaseState.PURCHASED) continue;
                    hasFull |= !FULL.isEmpty() && p.getProducts().contains(FULL);
                    hasAdFree |= !ADFREE.isEmpty() && p.getProducts().contains(ADFREE);
                    took(p);
                }
                if (!hasFull && full) setFull(false, "");
                if (!hasAdFree && adFree) setAdFree(false);
            });
    }

    private void details() {
        List<QueryProductDetailsParams.Product> want = new ArrayList<>();
        for (String id : new String[] {FULL, ADFREE}) {
            if (!id.isEmpty()) want.add(QueryProductDetailsParams.Product.newBuilder()
                .setProductId(id).setProductType(BillingClient.ProductType.INAPP).build());
        }
        client.queryProductDetailsAsync(QueryProductDetailsParams.newBuilder().setProductList(want).build(),
            (result, list) -> {
                if (result.getResponseCode() != BillingClient.BillingResponseCode.OK || list == null) return;
                for (ProductDetails d : list) {
                    products.put(d.getProductId(), d);
                    ProductDetails.OneTimePurchaseOfferDetails offer = d.getOneTimePurchaseOfferDetails();
                    if (offer != null) prices.put(d.getProductId(), offer.getFormattedPrice());
                }
            });
    }

    /** A button: Google Play's own payment sheet, for the full game or Remove ads. */
    void buy(String id) {
        if (id.isEmpty() || full || (id.equals(ADFREE) && adFree)) return;
        ProductDetails product = products.get(id);
        if (client == null || !client.isReady() || product == null) {
            if (client != null && !client.isReady()) connect();
            told.accept("failed");
            return;
        }
        List<BillingFlowParams.ProductDetailsParams> what = Collections.singletonList(
            BillingFlowParams.ProductDetailsParams.newBuilder().setProductDetails(product).build());
        activity.runOnUiThread(() -> client.launchBillingFlow(activity,
            BillingFlowParams.newBuilder().setProductDetailsParamsList(what).build()));
    }

    private void took(Purchase p) {
        boolean isFull = !FULL.isEmpty() && p.getProducts().contains(FULL);
        boolean isAdFree = !ADFREE.isEmpty() && p.getProducts().contains(ADFREE);
        if (!isFull && !isAdFree) return;
        if (p.getPurchaseState() == Purchase.PurchaseState.PENDING) {
            told.accept("pending");
            return;
        }
        if (p.getPurchaseState() != Purchase.PurchaseState.PURCHASED) return;
        if (!p.isAcknowledged()) {                     // (unacknowledged for three days, Google refunds it)
            client.acknowledgePurchase(AcknowledgePurchaseParams.newBuilder().setPurchaseToken(p.getPurchaseToken()).build(),
                (result) -> { });
        }
        if (isFull && (!full || !p.getPurchaseToken().equals(fullToken()))) {
            boolean was = full;
            setFull(true, p.getPurchaseToken());
            if (!was) told.accept("full");
        }
        if (isAdFree && !adFree) {
            setAdFree(true);
            if (!full) told.accept("bought");
        }
    }

    private void setFull(boolean yes, String token) {
        full = yes;
        prefs().edit().putBoolean("full_game", yes).putString("full_token", yes ? token : "").apply();
    }

    private void setAdFree(boolean yes) {
        adFree = yes;
        prefs().edit().putBoolean("ad_free", yes).apply();
    }

    void destroy() {
        if (client != null) client.endConnection();
    }
}
