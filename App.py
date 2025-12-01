with top1:
            # Critical Orders Section
            critical_df = df_day[(df_day['Order Type'] == 'Ad-hoc Critical') & 
                                 (~df_day['Order Status'].isin(['Shipped']))]
            critical_gis = critical_df['GINo'].unique().tolist() if not critical_df.empty else []
            critical_text = ", ".join(map(str, critical_gis))
            
            # Copy button with count
            if st.button(f"📋 Copy Critical GIs ({len(critical_gis)})", key=f"{i}_copy_critical", use_container_width=True):
                st.write("Copy this text:")
                st.code(critical_text if critical_text else "No critical orders", language=None)
            
            # Scrollable frame (always visible)
            st.markdown(
                f"""
                <div style='
                    max-height: 100px;
                    overflow-y: auto;
                    border: 1px solid #fecaca;
                    border-radius: 6px;
                    padding: 6px;
                    background-color: #fef2f2;
                    margin-top: 6px;
                    font-size: 12px;
                    min-height: 50px;
                '>
                    {
                        '<br>'.join([f"<span style='display:block; padding:1px 0;'>{gi}</span>" for gi in critical_gis])
                        if critical_gis else
                        "<span style='color:#9ca3af; font-style:italic;'>No critical orders</span>"
                    }
                </div>
                """,
                unsafe_allow_html=True
            )

            # Urgent Orders Section
            st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
            urgent_df = df_day[(df_day['Order Type'] == 'Ad-hoc Urgent') & 
                               (~df_day['Order Status'].isin(['Shipped']))]
            urgent_gis = urgent_df['GINo'].unique().tolist() if not urgent_df.empty else []
            urgent_text = ", ".join(map(str, urgent_gis))
            
            # Copy button with count
            if st.button(f"📋 Copy Urgent GIs ({len(urgent_gis)})", key=f"{i}_copy_urgent", use_container_width=True):
                st.write("Copy this text:")
                st.code(urgent_text if urgent_text else "No urgent orders", language=None)
            
            # Scrollable frame (always visible)
            st.markdown(
                f"""
                <div style='
                    max-height: 100px;
                    overflow-y: auto;
                    border: 1px solid #fde68a;
                    border-radius: 6px;
                    padding: 6px;
                    background-color: #fefce8;
                    margin-top: 6px;
                    font-size: 12px;
                    min-height: 50px;
                '>
                    {
                        '<br>'.join([f"<span style='display:block; padding:1px 0;'>{gi}</span>" for gi in urgent_gis])
                        if urgent_gis else
                        "<span style='color:#9ca3af; font-style:italic;'>No urgent orders</span>"
                    }
                </div>
                """,
                unsafe_allow_html=True
            )
