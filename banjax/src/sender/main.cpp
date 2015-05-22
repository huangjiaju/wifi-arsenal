/* -*- Mode: C++; tab-width: 3; -*- */

/* 
 * Copyright NICTA, 2011-2013
 */

#define __STDC_CONSTANT_MACROS
#define __STDC_LIMIT_MACROS
#include <metrics/airtime_metric_kernel.hpp>
#include <metrics/airtime_metric_linux.hpp>
#include <metrics/airtime_metric_measured.hpp>
#include <metrics/airtime_metric_ns3.hpp>
#include <metrics/elc_metric.hpp>
#include <metrics/elc_mrr_metric.hpp>
#include <metrics/etx_metric.hpp>
#include <metrics/fdr_metric.hpp>
#include <metrics/goodput_metric.hpp>
#include <metrics/iperf_metric.hpp>
#include <metrics/iperf_metric_wrapper.hpp>
#include <metrics/legacy_elc_metric.hpp>
#include <metrics/metric.hpp>
#include <metrics/metric_damper.hpp>
#include <metrics/metric_decimator.hpp>
#include <metrics/metric_demux.hpp>
#include <metrics/metric_group.hpp>
#include <metrics/pdr_metric.hpp>
#include <metrics/pktsz_metric.hpp>
#include <metrics/pkttime_metric.hpp>
#include <metrics/saturation_metric.hpp>
#include <metrics/simple_elc_metric.hpp>
#include <metrics/tmt_metric.hpp>
#include <metrics/txc_metric.hpp>

#include <dot11/data_frame.hpp>
#include <dot11/ip_hdr.hpp>
#include <dot11/llc_hdr.hpp>
#include <dot11/udp_hdr.hpp>

#include <net/buffer_info.hpp>
#include <net/ofdm_encoding.hpp>
#include <net/wnic.hpp>
#include <net/wnic_encoding_fix.hpp>
#include <net/wnic_require_timestamps.hpp>

#include <boost/program_options.hpp>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string.h>
#include <unistd.h>

using namespace boost;
using namespace boost::program_options;
using namespace dot11;
using namespace net;
using namespace metrics;
using namespace std;


static bool
is_iperf_packet(buffer_sptr b)
{
   // is it an iperf packet?
   frame f(b);
   data_frame_sptr df(f.as_data_frame());
   if(!df)
      return false;

   llc_hdr_sptr llc(df->get_llc_hdr());
   if(!llc)
      return false;

   ip_hdr_sptr ip(llc->get_ip_hdr());
   if(!ip)
      return false;

   udp_hdr_sptr udp(ip->get_udp_hdr());
   if(!udp)
      return false;

   if(udp->dst_port() != 5001)
      return false;

   return true;
}


static uint32_t
iperf_seq_no(buffer_sptr b)
{
   uint32_t packet = 0;
   if(is_iperf_packet(b)) {
      frame f(b);
      data_frame_sptr df(f.as_data_frame());
      llc_hdr_sptr llc(df->get_llc_hdr());
      ip_hdr_sptr ip(llc->get_ip_hdr());
      udp_hdr_sptr udp(ip->get_udp_hdr());
      buffer_sptr payload(udp->get_payload());
      packet = payload->read_u32(0);
   }
   return packet;
}


int
main(int ac, char **av)
{
   try {

      bool debug, help;
      string enc_str, what;
      uint16_t acktimeout;
      uint32_t dead_time;
      uint16_t cw; 
      uint16_t damp;
      uint16_t mpdu_sz;
      uint16_t port_no;
      uint16_t rts_cts_threshold;
      uint32_t rate_Mbs;
      uint64_t runtime;
      size_t window_sz;
      bool show_ticks;

      options_description options("program options");
      options.add_options()
         ("acktimeout,a", value(&acktimeout)->default_value(UINT16_MAX), "specify ACKTimeout value")
         ("cw,c", value(&cw)->default_value(UINT16_MAX), "size of contention window in microseconds (default = compute average)")
         ("damping,d", value(&damp)->default_value(5), "size of damping window in seconds")
         ("dead,e", value(&dead_time)->default_value(0), "dead time (in microseconds) per tick")
         ("debug,g", value<bool>(&debug)->default_value(false)->zero_tokens(), "enable debug")
         ("encoding", value<string>(&enc_str)->default_value("OFDM"), "channel encoding")
         ("help,?", value(&help)->default_value(false)->zero_tokens(), "produce this help message")
         ("input,i", value<string>(&what)->default_value("mon0"), "input file/device name")
         ("linkrate,l", value<uint32_t>(&rate_Mbs)->default_value(6), "link rate in Mb/s")
         ("mpdu,m", value<uint16_t>(&mpdu_sz)->default_value(1024), "MPDU size in octets")
         ("rts-threshold,r", value<uint16_t>(&rts_cts_threshold)->default_value(UINT16_MAX), "RTS threshold level")
         ("runtime,u", value<uint64_t>(&runtime)->default_value(0), "produce results after n seconds")
         ("ticks,t", value<bool>(&show_ticks)->default_value(false)->zero_tokens(), "show results for each second")
         ;

      variables_map vars;       
      store(parse_command_line(ac, av, options), vars);
      notify(vars);   
      if(help) {
         cout << options << endl;
         exit(EXIT_SUCCESS);
      }

      encoding_sptr enc(encoding::get(enc_str));
    	metric_group_sptr link_metrics(new metric_group);
      // link_metrics->push_back(metric_sptr(new airtime_metric_kernel));
      // link_metrics->push_back(metric_sptr(new metric_decimator("Airtime-Kernel-5PC", metric_sptr(new airtime_metric_kernel), 20)));
      link_metrics->push_back(metric_sptr(new airtime_metric_linux(enc)));
      link_metrics->push_back(metric_sptr(new airtime_metric_measured));
      link_metrics->push_back(metric_sptr(new airtime_metric_ns3(enc, rts_cts_threshold)));
      link_metrics->push_back(metric_sptr(new iperf_metric("iperf", false)));
      link_metrics->push_back(metric_sptr(new pkttime_metric));
      // link_metrics->push_back(metric_sptr(new tmt_metric(enc, rate_Mbs * 1000, mpdu_sz, rts_cts_threshold)));
      // link_metrics->push_back(metric_sptr(new fdr_metric));
      // link_metrics->push_back(metric_sptr(new pdr_metric));
      // link_metrics->push_back(metric_sptr(new goodput_metric));
      // link_metrics->push_back(metric_sptr(new txc_metric("TXC")));

    	metric_group_sptr chan_metrics(new metric_group);
      chan_metrics->push_back(metric_sptr(new saturation_metric));
      chan_metrics->push_back(metric_sptr(new iperf_metric_wrapper(metric_sptr(new metric_demux(link_metrics)))));
      metric_sptr metrics(chan_metrics);

      wnic_sptr w(wnic::open(what));
      if("OFDM" == enc_str) {
         w = wnic_sptr(new wnic_encoding_fix(w, CHANNEL_CODING_OFDM | CHANNEL_PREAMBLE_LONG));
      } else if("DSSS" == enc_str) {
         w = wnic_sptr(new wnic_encoding_fix(w, CHANNEL_CODING_DSSS | CHANNEL_PREAMBLE_LONG));
      }
      w = wnic_sptr(new wnic_require_timestamps(w));

      buffer_sptr b(w->read());
      if(b) {
         buffer_info_sptr info(b->info());
         uint64_t tick_time = UINT64_C(1000000);
         uint64_t start_time =  info->timestamp1();
         uint64_t end_time = runtime ? info->timestamp1() + (runtime * tick_time) : UINT64_MAX;
         uint64_t next_tick = show_ticks ? info->timestamp1() + tick_time : UINT64_MAX;
         while(b && (info->timestamp1() <= end_time)) {
            // is it time to print results yet?
            info = b->info();
            uint64_t timestamp = info->timestamp2();
            for(; next_tick <= timestamp; next_tick += tick_time) {
               metrics->compute(next_tick, tick_time);
               cout << "Time: " << (next_tick - start_time) / tick_time << ", " << *metrics << endl;
               metrics->reset();
            }
            if(debug && is_iperf_packet(b)) { 
               clog << iperf_seq_no(b) << " " << *info << endl;
            }
            metrics->add(b);
            b = w->read();
         }
         if(!show_ticks) {
            uint_least32_t elapsed = runtime * tick_time;
            metrics->compute(next_tick, elapsed);
            cout << "Time: " << static_cast<double>(elapsed) / tick_time << ", " << *metrics << endl;
         }
      }
   } catch(const error& x) {
      cerr << x.what() << endl;
   } catch(const std::exception& x) {
      cerr << x.what() << endl;
   } catch(...) {
      cerr << "unhandled exception!" << endl;
   }
   exit(EXIT_FAILURE);
}
