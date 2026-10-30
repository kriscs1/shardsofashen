package io.github.kriscs1.shardsofashen;

import android.app.Activity;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;

import java.util.function.Consumer;

import com.google.android.gms.ads.AdListener;
import com.google.android.gms.ads.AdRequest;
import com.google.android.gms.ads.AdSize;
import com.google.android.gms.ads.AdView;
import com.google.android.gms.ads.LoadAdError;
import com.google.android.gms.ads.MobileAds;
import com.google.android.ump.ConsentInformation;
import com.google.android.ump.ConsentRequestParameters;
import com.google.android.ump.UserMessagingPlatform;

/** AdMob: a banner along the bottom of the start screen while its menu shows, never in a game. Where the law wants
 *  it (the EEA, the UK) Google's consent form is asked first, and the start screen offers "Ad choices" to change it.
 *  The banner's unit is the build's (BuildConfig.ADMOB_BANNER): Google's test ads in a debug build, and none at all
 *  in a release built without one. The start screen is told when an ad's come (it makes room) or none could be had
 *  (it shows our own). */
class Ads {
    private final Activity activity;
    private final FrameLayout frame;
    private final Consumer<Boolean> told;
    private ConsentInformation consent;
    private AdView banner;
    private boolean started, ready, wanted;

    Ads(Activity activity, FrameLayout frame, Consumer<Boolean> told) {
        this.activity = activity;
        this.frame = frame;
        this.told = told;
    }

    static boolean on() {
        return !BuildConfig.ADMOB_BANNER.isEmpty();
    }

    /** As the app opens: consent (if it's needed and not given yet), then the SDK. */
    void start() {
        if (!on()) return;
        consent = UserMessagingPlatform.getConsentInformation(activity);
        consent.requestConsentInfoUpdate(activity, new ConsentRequestParameters.Builder().build(),
            () -> UserMessagingPlatform.loadAndShowConsentFormIfRequired(activity, (err) -> begin()),
            (err) -> begin());
        begin();                                        // (consent given last time: no need to wait)
    }

    private void begin() {
        if (started || !consent.canRequestAds()) return;
        started = true;
        new Thread(() -> MobileAds.initialize(activity, (status) -> activity.runOnUiThread(() -> {
            ready = true;
            apply();
        })), "ads").start();
    }

    /** The start screen's menu showing (yes) or gone (a game, signing in). */
    void show(boolean yes) {
        activity.runOnUiThread(() -> {
            wanted = yes;
            apply();
        });
    }

    private void apply() {
        if (!ready) return;
        if (wanted && banner == null) {
            banner = new AdView(activity);
            banner.setAdSize(AdSize.BANNER);            // (320 x 50: the start screen leaves room for it)
            banner.setAdUnitId(BuildConfig.ADMOB_BANNER);
            banner.setAdListener(new AdListener() {
                @Override
                public void onAdLoaded() {
                    if (wanted) told.accept(true);
                }

                @Override
                public void onAdFailedToLoad(LoadAdError err) {
                    told.accept(false);
                    frame.removeView(banner);           // (tried again the next time the menu shows)
                    banner.destroy();
                    banner = null;
                }
            });
            frame.addView(banner, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.WRAP_CONTENT,
                FrameLayout.LayoutParams.WRAP_CONTENT, Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL));
            banner.loadAd(new AdRequest.Builder().build());
        }
        if (banner != null) {
            if (wanted && banner.getResponseInfo() != null) told.accept(true);   // (loaded before: shown again)
            banner.setVisibility(wanted ? View.VISIBLE : View.GONE);
            if (wanted) banner.resume();
            else banner.pause();
        }
    }

    /** Whether the start screen should offer "Ad choices" (consent can be changed: the EEA and UK). */
    boolean choices() {
        return consent != null && consent.getPrivacyOptionsRequirementStatus()
            == ConsentInformation.PrivacyOptionsRequirementStatus.REQUIRED;
    }

    void showChoices() {
        activity.runOnUiThread(() -> UserMessagingPlatform.showPrivacyOptionsForm(activity, (err) -> begin()));
    }

    void destroy() {
        if (banner != null) banner.destroy();
    }
}
