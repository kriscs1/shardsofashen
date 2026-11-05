package io.github.kriscs1.shardsofashen;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;

import java.util.Collections;
import java.util.List;
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

/** "Remove ads": one payment through Google Play (the owner's wish), a one-time product (BuildConfig.ADFREE_PRODUCT,
 *  made in the Play Console). Bought, the start screen shows no ads again, on this device, and Google Play gives it back
 *  after a reinstall or on another phone with the same Google account (its purchases are asked for each time the app
 *  opens). The payment is Google's: the app never sees a card. The start screen is told when it's bought (or pending). */
class Billing {
    private final Activity activity;
    private final Consumer<String> told;              // ("bought", "pending", or "failed")
    private BillingClient client;
    private ProductDetails product;
    private volatile String price = "";
    private volatile boolean bought;

    Billing(Activity activity, Consumer<String> told) {
        this.activity = activity;
        this.told = told;
        bought = prefs().getBoolean("ad_free", false);  // (known at once, before Google Play answers)
    }

    static boolean on() {
        return !BuildConfig.ADFREE_PRODUCT.isEmpty();
    }

    private SharedPreferences prefs() {
        return activity.getSharedPreferences("start", Context.MODE_PRIVATE);
    }

    boolean adFree() {
        return bought;
    }

    /** The price as Google Play shows it here ("£1.99"), or "" until it's known (or there's nothing to buy). */
    String price() {
        return bought ? "" : price;
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
                // (asked again the next time the button's pressed)
            }
        });
    }

    /** What this Google account has bought: given back after a reinstall, or taken away after a refund. */
    private void restore() {
        client.queryPurchasesAsync(QueryPurchasesParams.newBuilder().setProductType(BillingClient.ProductType.INAPP).build(),
            (result, purchases) -> {
                if (result.getResponseCode() != BillingClient.BillingResponseCode.OK) return;
                boolean has = false;
                for (Purchase p : purchases) {
                    if (p.getProducts().contains(BuildConfig.ADFREE_PRODUCT)
                            && p.getPurchaseState() == Purchase.PurchaseState.PURCHASED) {
                        has = true;
                        took(p);
                    }
                }
                if (!has && bought) set(false);
            });
    }

    private void details() {
        QueryProductDetailsParams.Product want = QueryProductDetailsParams.Product.newBuilder()
            .setProductId(BuildConfig.ADFREE_PRODUCT).setProductType(BillingClient.ProductType.INAPP).build();
        client.queryProductDetailsAsync(QueryProductDetailsParams.newBuilder().setProductList(Collections.singletonList(want)).build(),
            (result, list) -> {
                if (result.getResponseCode() != BillingClient.BillingResponseCode.OK || list == null || list.isEmpty()) return;
                product = list.get(0);
                ProductDetails.OneTimePurchaseOfferDetails offer = product.getOneTimePurchaseOfferDetails();
                price = offer != null ? offer.getFormattedPrice() : "";
            });
    }

    /** The button: Google Play's own payment sheet. */
    void buy() {
        if (!on() || bought) return;
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
        if (!p.getProducts().contains(BuildConfig.ADFREE_PRODUCT)) return;
        if (p.getPurchaseState() == Purchase.PurchaseState.PENDING) {
            told.accept("pending");
            return;
        }
        if (p.getPurchaseState() != Purchase.PurchaseState.PURCHASED) return;
        if (!p.isAcknowledged()) {                     // (unacknowledged for three days, Google refunds it)
            client.acknowledgePurchase(AcknowledgePurchaseParams.newBuilder().setPurchaseToken(p.getPurchaseToken()).build(),
                (result) -> { });
        }
        if (!bought) {
            set(true);
            told.accept("bought");
        }
    }

    private void set(boolean yes) {
        bought = yes;
        prefs().edit().putBoolean("ad_free", yes).apply();
    }

    void destroy() {
        if (client != null) client.endConnection();
    }
}
