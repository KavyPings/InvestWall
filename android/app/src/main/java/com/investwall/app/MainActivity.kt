package com.investwall.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.investwall.app.ui.InvestWallRoot
import com.investwall.app.ui.theme.Background
import com.investwall.app.ui.theme.InvestWallTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContent {
            InvestWallTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = Background) {
                    InvestWallRoot()
                }
            }
        }
    }
}
