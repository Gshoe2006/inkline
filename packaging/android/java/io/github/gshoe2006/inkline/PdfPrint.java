// Inkline's Print on Android: hands the PDF Inkline wrote (as Save PDF writes it) to Android's print service, which
// shows the system print dialog: the printers Android knows (Wi-Fi, Mopria, a printer maker's plugin) or Save as PDF.
// Called from Python (inkapp/android_print.py) through pyjnius; packed into the APK by packaging/android/deploy.py.
package io.github.gshoe2006.inkline;

import android.app.Activity;
import android.content.Context;
import android.os.Bundle;
import android.os.CancellationSignal;
import android.os.ParcelFileDescriptor;
import android.print.PageRange;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintDocumentInfo;
import android.print.PrintManager;

import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

public class PdfPrint extends PrintDocumentAdapter {
    private final String path;
    private final String name;

    PdfPrint(String path, String name) {
        this.path = path;
        this.name = name;
    }

    /** Open the print dialog for the PDF at path, named name; duplex: a fold-and-staple booklet (short edge). */
    public static void start(final Activity activity, final String path, final String name, final boolean duplex) {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                PrintManager manager = (PrintManager) activity.getSystemService(Context.PRINT_SERVICE);
                PrintAttributes.Builder wanted = new PrintAttributes.Builder()
                        .setColorMode(PrintAttributes.COLOR_MODE_MONOCHROME);
                if (duplex) {
                    wanted.setDuplexMode(PrintAttributes.DUPLEX_MODE_SHORT_EDGE);
                }
                manager.print(name, new PdfPrint(path, name), wanted.build());
            }
        });
    }

    @Override
    public void onLayout(PrintAttributes oldAttributes, PrintAttributes newAttributes, CancellationSignal cancel,
                         LayoutResultCallback callback, Bundle extras) {
        if (cancel.isCanceled()) {
            callback.onLayoutCancelled();
            return;
        }
        String file = name.toLowerCase().endsWith(".pdf") ? name : name + ".pdf";
        PrintDocumentInfo info = new PrintDocumentInfo.Builder(file)
                .setContentType(PrintDocumentInfo.CONTENT_TYPE_DOCUMENT)
                .build();
        callback.onLayoutFinished(info, oldAttributes == null || !newAttributes.equals(oldAttributes));
    }

    @Override
    public void onWrite(PageRange[] pages, ParcelFileDescriptor destination, CancellationSignal cancel,
                        WriteResultCallback callback) {
        try (InputStream in = new FileInputStream(path);
             OutputStream out = new FileOutputStream(destination.getFileDescriptor())) {
            byte[] buffer = new byte[64 * 1024];
            int n;
            while ((n = in.read(buffer)) > 0) {
                if (cancel.isCanceled()) {
                    callback.onWriteCancelled();
                    return;
                }
                out.write(buffer, 0, n);
            }
            callback.onWriteFinished(new PageRange[]{PageRange.ALL_PAGES});
        } catch (IOException e) {
            callback.onWriteFailed(e.getMessage());
        }
    }
}
