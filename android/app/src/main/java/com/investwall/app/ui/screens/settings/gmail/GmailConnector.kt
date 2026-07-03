package com.investwall.app.ui.screens.settings.gmail

import android.content.Context
import android.util.Log
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException
import com.google.android.gms.common.api.Scope

/**
 * Google OAuth scaffold for Gmail access (PRD §5 email, tech-stack §3).
 *
 * This wires the real Google Sign-In flow and requests the Gmail read-only
 * scope. Fetching and analysing actual emails via the Gmail API is deferred to a
 * later phase (it additionally requires an OAuth client configured in Google
 * Cloud with this app's package + SHA-1). Until then, connecting simply records
 * the chosen account so the UI reflects the connection.
 */
class GmailConnector(
    private val client: GoogleSignInClient,
    private val launchSignIn: () -> Unit,
    private val onConnected: (String) -> Unit,
) {
    fun connect() = launchSignIn()

    fun disconnect() {
        runCatching { client.signOut() }
    }

    fun handleResult(data: android.content.Intent?) {
        try {
            val account = GoogleSignIn.getSignedInAccountFromIntent(data)
                .getResult(ApiException::class.java)
            account?.email?.let(onConnected)
        } catch (e: ApiException) {
            Log.w("GmailConnector", "Sign-in failed: ${e.statusCode}")
        }
    }

    companion object {
        val GMAIL_READONLY = Scope("https://www.googleapis.com/auth/gmail.readonly")

        fun buildClient(context: Context): GoogleSignInClient {
            val options = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
                .requestEmail()
                .requestScopes(GMAIL_READONLY)
                .build()
            return GoogleSignIn.getClient(context, options)
        }
    }
}

/** Compose helper that owns the sign-in ActivityResult launcher. */
@Composable
fun rememberGmailConnector(onConnected: (String) -> Unit): GmailConnector {
    val context = LocalContext.current
    val client = remember { GmailConnector.buildClient(context) }

    // Holder so the connector (created before the launcher) can invoke it.
    val connectorHolder = remember { arrayOfNulls<GmailConnector>(1) }

    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult(),
    ) { result -> connectorHolder[0]?.handleResult(result.data) }

    return remember {
        GmailConnector(
            client = client,
            launchSignIn = { launcher.launch(client.signInIntent) },
            onConnected = onConnected,
        ).also { connectorHolder[0] = it }
    }
}
